import pytest

import varlink


def test_scanner_1():
    interface = varlink.Interface("""# Example Varlink service
interface org.example.more

# Enum, returning either start, progress or end
# progress: [0-100]
type State (
  start: ?bool,
  progress: ?int,
  end: ?bool
)

method TestMap(map: [string]string) -> (map: [string](i: int, val: string))

# Returns the same string
method Ping(ping: string) -> (pong: string)

# Dummy progress method
# n: number of progress steps
method TestMore(n: int) -> (state: State)

# Stop serving
method StopServing() -> ()

type ErrorChain (
    description: string,
    caused_by: ?ErrorChain
)

error ActionFailed (reason: ?ErrorChain)
""")
    assert interface.name == "org.example.more"
    assert interface.get_method("Ping") is not None
    assert interface.get_method("TestMore") is not None
    assert interface.get_method("TestMap") is not None
    assert interface.get_method("StopServing") is not None
    assert isinstance(interface.members.get("ActionFailed"), varlink.scanner._Error)
    assert isinstance(interface.members.get("State"), varlink.scanner._Alias)


def test_doubleoption():
    interface = None
    try:
        interface = varlink.Interface("""
interface org.example.doubleoption
method Foo(a: ??string) -> ()
""")
    except SyntaxError:
        pass

    assert interface is None


def test_complex():
    interface = varlink.Interface("""
interface org.example.complex

type TypeEnum ( a, b, c )

type TypeFoo (
    bool: bool,
    int: int,
    float: float,
    string: ?string,
    enum: ?[]( foo, bar, baz ),
    type: ?TypeEnum,
    anon: ( foo: bool, bar: int, baz: [](a: int, b: int) ),
    object: object
)

method Foo(a: (b: bool, c: int), foo: TypeFoo) -> (a: [](b: bool, c: int), foo: TypeFoo)

error ErrorFoo (a: (b: bool, c: int), foo: TypeFoo)
""")

    assert interface.name == "org.example.complex"
    assert interface.get_method("Foo") is not None
    assert isinstance(interface.members.get("ErrorFoo"), varlink.scanner._Error)
    assert isinstance(interface.members.get("TypeEnum"), varlink.scanner._Alias)


def test_interfacename():
    with pytest.raises(SyntaxError):
        varlink.Interface("interface .a.b.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface com.-example.leadinghyphen\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface com.example-.danglinghyphen-\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface co9.example.number-toplevel\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface 1om.example.number-toplevel\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface ab\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface .a.b.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.b.c.\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a..b.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface 1.b.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface 8a.0.0\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface -a.b.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.b.c-\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.b-.c-\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.-b.c-\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.-.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.*.c\nmethod F()->()")
    with pytest.raises(SyntaxError):
        varlink.Interface("interface a.?\nmethod F()->()")

    assert varlink.Interface("interface a.b\nmethod F()->()").name is not None
    assert varlink.Interface("interface a.b.c\nmethod F()->()").name is not None
    assert varlink.Interface("interface a.1\nmethod F()->()").name is not None
    assert varlink.Interface("interface a.0.0\nmethod F()->()").name is not None
    assert varlink.Interface("interface org.varlink.service\nmethod F()->()").name is not None
    assert varlink.Interface("interface com.example.0example\nmethod F()->()").name is not None
    assert varlink.Interface("interface com.example.example-dash\nmethod F()->()").name is not None
    assert varlink.Interface("interface xn--lgbbat1ad8j.example.algeria\nmethod F()->()").name is not None
    assert (
        varlink.Interface("interface xn--c1yn36f.xn--c1yn36f.xn--c1yn36f\nmethod F()->()").name is not None
    )
