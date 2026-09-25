from lark import Token, Transformer, v_args

from .nodes import (
    AbsCall,
    Array,
    ArrayAddCall,
    ArrayRemoveCall,
    AssignStmt,
    BinOp,
    Bool,
    BreakStmt,
    CallExpr,
    CallStmt,
    Char,
    ChrCall,
    CodeCall,
    ContinueStmt,
    EndsCall,
    FileAppendCall,
    FileDeleteCall,
    FileExistsCall,
    FileReadCall,
    FileWriteCall,
    FindCall,
    ForInStmt,
    ForStmt,
    FromStmt,
    IfStmt,
    IndexGet,
    InputExpr,
    ImportStmt,
    JoinCall,
    LengthCall,
    LowerCall,
    MemberGet,
    ModCall,
    Node,
    Null,
    Number,
    Object,
    PrintStmt,
    ProcDef,
    RandomCall,
    RepeatStmt,
    ReplaceCall,
    ReturnStmt,
    ReverseCall,
    RoundCall,
    SplitCall,
    SqrtCall,
    StartsCall,
    String,
    SubstrCall,
    SwitchStmt,
    ToNumberCall,
    ToStringCall,
    UnaryNeg,
    UnaryNot,
    UpperCall,
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

    def print_stmt(self, _keyword, _open, expr, _close):
        return PrintStmt(expr=expr)

    def call_stmt(self, *children):
        name = _call_name(children)
        args = _arglist_of(children)
        return CallStmt(name=name, args=args)

    def import_stmt(self, *children):
        name = str(children[1])
        alias = str(children[3]) if len(children) == 4 else None
        return ImportStmt(name=name, alias=alias)

    def from_stmt(self, *children):
        return FromStmt(module=str(children[1]), names=children[3])

    def imported_names(self, *children):
        if len(children) == 1 and isinstance(children[0], Token) and children[0].type == "ALL":
            return "*"
        return [c for c in children if isinstance(c, tuple)]

    def imported_name(self, *children):
        name = str(children[0])
        alias = str(children[2]) if len(children) == 3 else None
        return (name, alias)

    def assign_stmt(self, *children):
        if len(children) == 4:  # запомнить имя = выражение
            return AssignStmt(target=str(children[1]), expr=children[3], is_declaration=True)
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

    def switch_stmt(self, *children):
        cases = []
        else_body = []
        for child in children[2:-1]:
            if isinstance(child, tuple):
                if len(child) == 2:
                    cases.append(child)
                else:
                    else_body = child[0]
        return SwitchStmt(expr=children[1], cases=cases, else_body=else_body)

    def case_part(self, *children):
        lists = [c for c in children if isinstance(c, list)]
        return (lists[0], lists[1])

    def case_values(self, *children):
        return [c for c in children if isinstance(c, Node)]

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

    def for_in_stmt(self, *children):
        return ForInStmt(
            var=str(children[1]),
            iterable=children[3],
            body=children[4],
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

    def break_stmt(self, *children):
        return BreakStmt()

    def continue_stmt(self, *children):
        return ContinueStmt()

    def array_add_stmt(self, *children):
        return ArrayAddCall(array=children[2], value=children[4])

    def array_remove_stmt(self, *children):
        return ArrayRemoveCall(array=children[2], index=children[4])

    def file_read_stmt(self, *children):
        return FileReadCall(arg=children[2])

    def file_write_stmt(self, *children):
        return FileWriteCall(path=children[2], text=children[4])

    def file_append_stmt(self, *children):
        return FileAppendCall(path=children[2], text=children[4])

    def file_exists_stmt(self, *children):
        return FileExistsCall(arg=children[2])

    def file_delete_stmt(self, *children):
        return FileDeleteCall(arg=children[2])

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

    def code_call(self, *children):
        return CodeCall(arg=children[2])

    def chr_call(self, *children):
        return ChrCall(arg=children[2])

    def find_call(self, *children):
        return FindCall(haystack=children[2], needle=children[4])

    def substr_call(self, *children):
        return SubstrCall(string=children[2], start=children[4], length=children[6])

    def array_add_call(self, *children):
        return ArrayAddCall(array=children[2], value=children[4])

    def array_remove_call(self, *children):
        return ArrayRemoveCall(array=children[2], index=children[4])

    def sqrt_call(self, *children):
        return SqrtCall(arg=children[2])

    def abs_call(self, *children):
        return AbsCall(arg=children[2])

    def random_call(self, *children):
        nodes = [c for c in children if isinstance(c, Node)]
        if len(nodes) == 1:
            return RandomCall(high=nodes[0])
        return RandomCall(low=nodes[0], high=nodes[1])

    def mod_call(self, *children):
        return ModCall(left=children[2], right=children[4])

    def round_call(self, *children):
        return RoundCall(arg=children[2])

    def upper_call(self, *children):
        return UpperCall(arg=children[2])

    def lower_call(self, *children):
        return LowerCall(arg=children[2])

    def replace_call(self, *children):
        return ReplaceCall(string=children[2], old=children[4], new=children[6])

    def split_call(self, *children):
        return SplitCall(string=children[2], separator=children[4])

    def join_call(self, *children):
        return JoinCall(array=children[2], separator=children[4])

    def starts_call(self, *children):
        return StartsCall(string=children[2], prefix=children[4])

    def ends_call(self, *children):
        return EndsCall(string=children[2], suffix=children[4])

    def reverse_call(self, *children):
        return ReverseCall(arg=children[2])

    def file_read_call(self, *children):
        return FileReadCall(arg=children[2])

    def file_write_call(self, *children):
        return FileWriteCall(path=children[2], text=children[4])

    def file_append_call(self, *children):
        return FileAppendCall(path=children[2], text=children[4])

    def file_exists_call(self, *children):
        return FileExistsCall(arg=children[2])

    def file_delete_call(self, *children):
        return FileDeleteCall(arg=children[2])

    def to_number(self, *children):
        return ToNumberCall(arg=children[2])

    def to_string(self, *children):
        return ToStringCall(arg=children[2])

    def call_expr(self, *children):
        name = _call_name(children)
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


def _call_name(children):
    """Склеить имя вызова: «имя» или «модуль.процедура»."""
    names = [
        str(c)
        for c in children[1:]
        if isinstance(c, Token) and c.type == "NAME"
    ]
    return ".".join(names[:2])


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