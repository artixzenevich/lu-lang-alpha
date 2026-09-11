from lark import Token, Transformer, v_args

from .nodes import (
    Array,
    AssignStmt,
    BinOp,
    Bool,
    CallExpr,
    CallStmt,
    Char,
    ForStmt,
    IfStmt,
    IndexGet,
    InputExpr,
    LengthCall,
    MemberGet,
    Node,
    Null,
    Number,
    Object,
    PrintStmt,
    ProcDef,
    RepeatStmt,
    ReturnStmt,
    String,
    UnaryNeg,
    UnaryNot,
    Variable,
    WhileStmt,
)


@v_args(inline=True)
class AstBuilder(Transformer):
    """Transformer Lark, который строит узлы AST."""

    def start(self, *stmts):
        return [s for s in stmts if s is not None]

    def empty_stmt(self, *args):
        return None

    # --- инструкции -------------------------------------------------------

    def print_stmt(self, _keyword, _colon, expr):
        return PrintStmt(expr=expr)

    def call_stmt(self, *children):
        name = str(children[1])
        args = _arglist_of(children)
        return CallStmt(name=name, args=args)

    def assign_stmt(self, *children):
        if len(children) == 4:  # запомнить имя = выражение
            return AssignStmt(target=str(children[1]), expr=children[3])
        return AssignStmt(target=children[0], expr=children[2])

    def lvalue(self, *children):
        if len(children) == 1:
            return str(children[0])
        if len(children) == 3 and children[1].type == "DOT":
            return MemberGet(obj=Variable(name=str(children[0])), name=str(children[2]))
        return IndexGet(obj=Variable(name=str(children[0])), index=children[2])

    def if_stmt(self, *children):
        branches = [(children[1], children[3])]
        else_body = []
        for child in children[4:-1]:
            if isinstance(child, tuple):
                if len(child) == 2:
                    branches.append(child)
                else:
                    else_body = child[0]
        return IfStmt(branches=branches, else_body=else_body)

    def elif_part(self, *children):
        return (children[2], children[4])

    def else_part(self, *children):
        return (children[1],)

    def stmts(self, *children):
        return [c for c in children if isinstance(c, Node)]

    def while_stmt(self, *children):
        return WhileStmt(cond=children[1], body=children[2])

    def for_stmt(self, *children):
        return ForStmt(
            var=str(children[1]),
            start=children[3],
            end=children[5],
            body=children[6],
        )

    def repeat_stmt(self, *children):
        return RepeatStmt(count=children[1], body=children[3])

    def proc_def(self, *children):
        name = str(children[1])
        rest = list(children[3:-1])
        params = []
        body = []
        if rest and isinstance(rest[0], list) and (
            not rest[0] or all(isinstance(x, str) for x in rest[0])
        ):
            params = rest.pop(0)
        for part in rest:
            if isinstance(part, list):
                body = part
        return ProcDef(name=name, params=params, body=body)

    def params(self, *children):
        return [str(c) for c in children if isinstance(c, Token) and c.type == "NAME"]

    def return_stmt(self, *children):
        return ReturnStmt(expr=children[1] if len(children) > 1 else None)

    # --- выражения --------------------------------------------------------

    def or_expr(self, *args):
        return _fold_binary(args)

    def and_expr(self, *args):
        return _fold_binary(args)

    def additive(self, *args):
        return _fold_binary(args)

    def multiplicative(self, *args):
        return _fold_binary(args)

    def not_op(self, _keyword, operand):
        return UnaryNot(operand=operand)

    def comparison(self, *children):
        if len(children) == 1:
            return children[0]
        return BinOp(op=str(children[1]), left=children[0], right=children[2])

    def neg(self, _minus, operand):
        return UnaryNeg(operand=operand)

    def index_get(self, *children):
        return IndexGet(obj=children[0], index=children[2])

    def member_get(self, *children):
        return MemberGet(obj=children[0], name=str(children[2]))

    def length_call(self, *children):
        return LengthCall(arg=children[2])

    def call_expr(self, *children):
        name = str(children[1])
        args = _arglist_of(children)
        return CallExpr(name=name, args=args)

    def call_tail_expr(self, *children):
        if len(children) == 1:
            return children[0]
        return BinOp(op=str(children[1]), left=children[0], right=children[2])

    def arglist(self, *children):
        return [c for c in children if isinstance(c, Node)]

    def array_literal(self, *children):
        return Array(items=[c for c in children if isinstance(c, Node)])

    def object_literal(self, *children):
        fields = {}
        current_key = None
        for child in children:
            if isinstance(child, Token):
                if child.type == "NAME":
                    current_key = str(child)
            elif isinstance(child, Node) and current_key is not None:
                fields[current_key] = child
                current_key = None
        return Object(fields=fields)

    def input(self, *children):
        return InputExpr()

    def atom(self, *children):
        if len(children) == 3 and isinstance(children[0], Token):
            return children[1]
        return children[0]

    # --- простые значения ---------------------------------------------------

    def number(self, token):
        return Number(value=float(token))

    def string(self, token):
        return String(value=token[1:-1])

    def char(self, token):
        return Char(value=token[1:-1])

    def true(self, *children):
        return Bool(value=True)

    def false(self, *children):
        return Bool(value=False)

    def null(self, *children):
        return Null()

    def variable(self, token):
        return Variable(name=str(token))


def _nodes(children):
    return [c for c in children if isinstance(c, Node)]


def _arglist_of(children):
    """Найти список аргументов среди потомков вызова (может отсутствовать)."""
    return next((c for c in children[2:] if isinstance(c, list)), [])


def _fold_binary(args):
    result = args[0]
    for op, right in zip(args[1::2], args[2::2]):
        result = BinOp(op=str(op), left=result, right=right)
    return result


def build_ast(tree) -> list:
    """Превратить дерево Lark в программу (список инструкций AST)."""
    return AstBuilder().transform(tree)