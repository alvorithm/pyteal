import json

import algosdk

from pyteal import (
    ABIReturnSubroutine,
    App,
    BareCallActions,
    Expr,
    Int,
    Len,
    Mode,
    OnCompleteAction,
    Pop,
    Router,
    Seq,
    abi,
)

from tests.blackbox import Blackbox, PyTealDryRunExecutor


@Blackbox(input_types=[None, None])
@ABIReturnSubroutine
def boxer(name: abi.String, value: abi.String, *, output: abi.Bool) -> Expr:
    # return Seq(
    #     output.set(Int(1)),
    # )
    return Seq(
        output.set(App.box_create(name.get(), Len(value.get()))),
        # App.box_put(name.get(), value.get()),
    )


def test_boxer():
    ptdre = PyTealDryRunExecutor(boxer, Mode.Application)

    assert [
        algosdk.abi.StringType(),
        algosdk.abi.StringType(),
    ] == ptdre.abi_argument_types()
    assert algosdk.abi.BoolType() == ptdre.abi_return_type()

    inputs = [
        ("hello", "world"),
        (
            "this box creation will error because its name has length 65 > 64!",
            "erroring",
        ),
        (
            "this box creation will be just fine with a max name length == 64",
            "COPACETIC!",
        ),
        ("", ""),
    ]

    inspectors = ptdre.dryrun_on_sequence(inputs, compiler_version=8)
    x = 42


def on_delete() -> Expr:
    return Pop(Int(1))


router = Router(
    name="OpenPollingApp",
    descr="This is a polling application with no restrictions on who can participate.",
    bare_calls=BareCallActions(
        delete_application=OnCompleteAction.call_only(on_delete())
    ),
)


def test_router_v1():
    a, c, j = router.compile_program(version=8)

    print(f"router v1:{json.dumps(j.dictify(), indent=2)}")
