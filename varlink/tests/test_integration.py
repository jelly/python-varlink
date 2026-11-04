import pytest

import varlink


@pytest.mark.integration
def test_hostnamed():
    interface_name = "io.systemd.Hostname"
    client = varlink.Client(f"unix:/run/systemd/{interface_name}")
    interface = client.open(interface_name)

    host_information = interface.Describe()
    assert "Chassis" in host_information


@pytest.mark.integration
def test_expectmore():
    interface_name = "io.systemd.Login"
    client = varlink.Client(f"unix:/run/systemd/{interface_name}")
    interface = client.open(interface_name)

    with pytest.raises(varlink.ExpectedMore):
        interface.ListSessions()

    for message in interface.ListSessions(_more=True):
        assert message is not None
