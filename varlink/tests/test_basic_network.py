import json
import os
import socket
import sys
import threading

import pytest

import varlink

service = varlink.Service(
    vendor="Varlink",
    product="Varlink Examples",
    version="1",
    url="http://varlink.org",
    interface_dir=os.path.dirname(__file__),
)


class ServiceRequestHandler(varlink.RequestHandler):
    service = service


@pytest.mark.parametrize(
    "address,skip,skip_reason",
    [
        ("tcp:127.0.0.1:23450", False, ""),
        (
            f"unix:@org.varlink.service_anon_test{os.getpid()}{threading.current_thread().name}",
            not sys.platform.startswith("linux"),
            "Only runs on Linux",
        ),
        (
            f"unix:org.varlink.service_anon_test_{os.getpid()}{threading.current_thread().name}",
            not hasattr(socket, "AF_UNIX"),
            "No UNIX socket support",
        ),
    ],
)
def test_address(server_factory, address, skip, skip_reason) -> None:
    if skip:
        pytest.skip(skip_reason)

    server_factory(address, service)

    with varlink.Client(address) as client, client.open("org.varlink.service") as connection:
        info = connection.GetInfo()

        assert len(info["interfaces"]) == 1
        assert info["interfaces"][0] == "org.varlink.service"
        assert info == service.GetInfo()

        desc = connection.GetInterfaceDescription(info["interfaces"][0])
        assert desc == service.GetInterfaceDescription("org.varlink.service")

        connection.close()


def test_reuse_open(server_factory) -> None:
    address = "tcp:127.0.0.1:23450"
    server_factory(address, service)

    with varlink.Client(address) as client:
        connection = client.open_connection()
        re_use = client.open("org.varlink.service", False, connection)
        info = re_use.GetInfo()

        assert len(info["interfaces"]) == 1
        assert info["interfaces"][0] == "org.varlink.service"
        assert info == service.GetInfo()
        connection.close()


def test_wrong_url(server_factory) -> None:
    address = f"uenix:org.varlink.service_wrong_url_test_{os.getpid()}"
    with pytest.raises(ConnectionError):
        server_factory(address, service)


CONFLICTING_FLAGS = [
    {"oneway": True, "more": True},
    {"oneway": True, "upgrade": True},
    {"more": True, "upgrade": True},
    {"oneway": True, "more": True, "upgrade": True},
]


def _connect(address: str) -> socket.socket:
    if address.startswith("tcp:"):
        host, _, port = address[4:].rpartition(":")
        connection = socket.create_connection((host, int(port)))
    else:
        connection = socket.socket(socket.AF_UNIX)
        connection.connect(address[5:].replace("@", "\0", 1))
    connection.settimeout(2)
    return connection


def _call(address: str, message: dict) -> bytes:
    """Send a raw call and return what the server answers; b"" means the connection was closed."""
    with _connect(address) as connection:
        connection.sendall((json.dumps(message) + "\0").encode("utf-8"))
        return connection.recv(4096)


@pytest.fixture(
    params=[
        pytest.param("tcp", id="tcp"),
        pytest.param(
            "unix",
            id="unix",
            marks=pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="No UNIX socket support"),
        ),
        pytest.param(
            "abstract",
            id="abstract",
            marks=pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Only runs on Linux"),
        ),
    ]
)
def address(request, tmp_path) -> str:
    if request.param == "tcp":
        return "tcp:127.0.0.1:23452"
    if request.param == "unix":
        return f"unix:{tmp_path / 'varlink.sock'}"
    return f"unix:@org.varlink.service_flags_test_{os.getpid()}"


@pytest.mark.parametrize("flags", CONFLICTING_FLAGS)
def test_conflicting_call_flags_close_connection(server_factory, address, flags) -> None:
    server_factory(address, service)

    assert _call(address, {"method": "org.varlink.service.GetInfo", **flags}) == b""


@pytest.mark.parametrize(
    "call",
    [
        {"method": "org.example.Unknown.Method"},
        {"method": "org.varlink.service.NoSuchMethod"},
        {"method": "org.varlink.service.GetInfo", "parameters": {"bogus": 1}},
    ],
    ids=["unknown-interface", "unknown-method", "invalid-parameter"],
)
def test_conflicting_call_flags_close_connection_before_dispatch(server_factory, address, call) -> None:
    """The connection is closed, not answered with an error, even if the call would have failed anyway."""
    server_factory(address, service)

    assert _call(address, {**call, "oneway": True, "more": True}) == b""


@pytest.mark.parametrize(
    "flags",
    [{}, {"more": True}, {"more": True, "oneway": False, "upgrade": False}, {"oneway": False}],
)
def test_single_call_flag_is_accepted(server_factory, address, flags) -> None:
    server_factory(address, service)

    reply = json.loads(_call(address, {"method": "org.varlink.service.GetInfo", **flags}).rstrip(b"\0"))

    assert reply["parameters"] == service.GetInfo()


def test_connection_stays_usable_after_other_connection_is_closed(server_factory, address) -> None:
    server_factory(address, service)

    assert _call(address, {"method": "org.varlink.service.GetInfo", "oneway": True, "more": True}) == b""

    reply = json.loads(_call(address, {"method": "org.varlink.service.GetInfo"}).rstrip(b"\0"))
    assert reply["parameters"] == service.GetInfo()


@pytest.mark.parametrize("flags", CONFLICTING_FLAGS)
def test_service_handle_raises_invalid_call(flags) -> None:
    message = json.dumps({"method": "org.varlink.service.GetInfo", **flags}).encode("utf-8")

    with pytest.raises(varlink.MalformedCall):
        next(service.handle(message))
