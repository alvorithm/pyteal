from typing import Iterable
from build.lib.pyteal.ast.txn import TxnExprBuilder
from pyteal import *
from pyteal.ast.comment import CommentExpr
from pyteal.ast.return_ import ExitProgram

slots_in_use: dict[int, ScratchSlot] = {}

op_lookup = {str(op):op.name  for op in Op}

class SerializedExpr:
    def __init__(self, name: str, args: list["SerializedExpr"]):
        self.name = name
        self.args = args

    @staticmethod
    def from_expr(e: Expr) -> "SerializedExpr":
        nested_args: list[SerializedExpr] = []
        name: str = ""

        match e:
            case Seq() | Cond() | NaryExpr():
                for arg in e.args:
                    if isinstance(arg, Iterable):
                        for x in arg:
                            nested_args.append(SerializedExpr.from_expr(x))
                    else:
                        nested_args.append(SerializedExpr.from_expr(arg))
            case BinaryExpr():
                nested_args.append(SerializedExpr.from_expr(e.argLeft))
                nested_args.append(SerializedExpr.from_expr(e.argRight))
            case Assert():
                for cond in e.cond:
                    nested_args.append(SerializedExpr.from_expr(cond))
            case App():
                field = str(e.field).split(".")[1]
                name = "App." + field
                for arg in e.args:
                    nested_args.append(SerializedExpr.from_expr(arg))
            case Int():
                nested_args.append(SerializedExpr.from_expr(e.value))
            case Bytes():
                nested_args.append(
                    SerializedExpr.from_expr(e.byte_str.replace('"', ""))
                )
            case TxnExpr():
                field = str(e.field).split(".")[1]
                name = "Txn." + field
            case UnaryExpr():
                nested_args.append(SerializedExpr.from_expr(e.arg))
            case TxnaExpr():
                field = str(e.field).split(".")[1]
                name = f"Txna.{field}"
                nested_args.append(SerializedExpr.from_expr(e.index))
            case Return():
                nested_args.append(SerializedExpr.from_expr(e.value))
            case If():
                nested_args.append(SerializedExpr.from_expr(e.cond))
                nested_args.append(SerializedExpr.from_expr(e.thenBranch))
                if e.elseBranch is not None:
                    nested_args.append(SerializedExpr.from_expr(e.elseBranch))
            case Global():
                field = str(e.field).split(".")[1]
                name = "Global." + field
            case MultiValue():
                if len(e.immediate_args) > 0:
                    nested_args.append(SerializedExpr.from_expr(e.immediate_args))

                for arg in e.args:
                    nested_args.append(SerializedExpr.from_expr(arg))

                for os in e.output_slots:
                    nested_args.append(SerializedExpr.from_expr(os))

                if e.op.name == "app_local_get_ex":
                    name = "App.localGetEx"
                elif e.op.name == "app_global_get_ex":
                    name = "App.globalGetEx"

            case EnumInt():
                name = "OnComplete." + e.name
            case ScratchSlot():
                nested_args.append(SerializedExpr.from_expr(e.id))
            case ScratchStackStore():
                if e.slot is not None:
                    nested_args.append(SerializedExpr.from_expr(e.slot))
            case ScratchLoad():
                if e.slot is not None:
                    nested_args.append(SerializedExpr.from_expr(e.slot))
            case ScratchStore():
                if e.slot is not None:
                    nested_args.append(SerializedExpr.from_expr(e.slot))
                nested_args.append(SerializedExpr.from_expr(e.value))
            case ExitProgram():
                name = "ExitProgram"
                nested_args.append(SerializedExpr.from_expr(e.success))
            case CommentExpr():
                name="Comment"
                #nested_args.append(e.comment)
            case int() | str() | bytes():
                pass
            case _:
                print(f"unhandled: {e.__class__}")
                pass

        if name == "":
            if hasattr(e, "op"):
                name = str(e.op)
                #name = e.op.name.title().replace("_", "")
                #if name == "LogicAnd":
                #    name = "And"
            elif len(nested_args) == 0:
                name = e[1] if type(e) is tuple else str(e)
            else:
                name = e.__class__.__name__

        return SerializedExpr(name, nested_args)

    @staticmethod
    def undictify(d: dict) -> "SerializedExpr":
        return SerializedExpr(
            d["name"], [SerializedExpr.undictify(arg) for arg in d["args"]]
        )

    def to_expr(self) -> Expr:
        if self.name == "Int":
            return Int(int(self.args[0].name))
        elif self.name == "Bytes":
            return Bytes(str(self.args[0].name))
        elif self.name == "Cond":
            args = [arg.to_expr() for arg in self.args]
            return Cond(*[[args[idx], args[idx + 1]] for idx in range(0, len(args), 2)])
        elif self.name == "Txn":
            field_name = self.args[0].name.split(".")[1]
            return getattr(Txn, field_name)()
        elif self.name.startswith("Txna"):
            field_name = self.name.split(".")[1]
            return getattr(Txn, field_name)[self.args[0].to_expr()]
        elif self.name == "ScratchSlot":
            id = int(self.args[0].name)
            if id in slots_in_use:
                return slots_in_use[id]
            ss = ScratchSlot()
            ss.id = id
            slots_in_use[id] = ss
            return ss
        elif self.name == "App.globalGetEx":
            args = [arg.to_expr() for arg in self.args]
            expr = eval(self.name)(*args[:-2])
            expr.output_slots = args[-2:]
            return expr
        elif self.name == "App.localGetEx":
            args = [arg.to_expr() for arg in self.args]
            expr = eval(self.name)(*args[:-2])
            expr.output_slots = args[-2:]
            return expr
        elif self.name.startswith("OnComplete"):
            return eval(self.name)
        elif self.name in op_lookup:
            self.name = op_lookup[self.name].title()

        args = [arg.to_expr() for arg in self.args]
        thing = eval(self.name)
        if type(thing) is int:
            return thing

        return thing(*args)

    def dictify(self) -> dict:
        d = {"name": self.name, "args": [a.dictify() for a in self.args]}
        if len(d["args"]) == 0:
            del d["args"]
        return d


if __name__ == "__main__":

    program = Seq(
        If(Txn.application_id() == Int(0)).Then(
            Approve()
        )
    )

    se = SerializedExpr.from_expr(program)
    regen_program = se.to_expr()

    import json
    print(se.dictify())
    js = json.dumps(se.dictify(), indent=2)
    print(js)


    # co = CompileOptions(mode=Mode.Application, version=7)

    # expected, _ = program.__teal__(co)
    # expected.addIncoming()
    # expected = TealBlock.NormalizeBlocks(expected)

    # actual, _ = regen_program.__teal__(co)
    # actual.addIncoming()
    # actual = TealBlock.NormalizeBlocks(actual)

    # with TealComponent.Context.ignoreExprEquality(), TealComponent.Context.ignoreScratchSlotEquality():
    #    assert actual == expected

    # print(expected)
    # print(actual)

    #pcomp = compileTeal(program, mode=Mode.Application, version=7).split("\n")
    #rgcomp = compileTeal(regen_program, mode=Mode.Application, version=7).split("\n")
    #for idx in range(len(pcomp)):
    #    print(idx, pcomp[idx])
    #    print(idx, rgcomp[idx])