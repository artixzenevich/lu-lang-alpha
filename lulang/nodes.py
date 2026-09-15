"""Узлы абстрактного синтаксического дерева (AST)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


class Node:
    """Базовый класс для всех узлов AST."""


@dataclass
class Number(Node):
    value: float


@dataclass
class String(Node):
    value: str


@dataclass
class Char(Node):
    value: str


@dataclass
class Bool(Node):
    value: bool


@dataclass
class Null(Node):
    pass


@dataclass
class Variable(Node):
    name: str


@dataclass
class Array(Node):
    items: list


@dataclass
class Object(Node):
    fields: dict


@dataclass
class UnaryNeg(Node):
    operand: Node


@dataclass
class UnaryNot(Node):
    operand: Node


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class IndexGet(Node):
    obj: Node
    index: Node


@dataclass
class MemberGet(Node):
    obj: Node
    name: str


@dataclass
class LengthCall(Node):
    arg: Node


@dataclass
class CodeCall(Node):
    arg: Node


@dataclass
class ChrCall(Node):
    arg: Node


@dataclass
class FindCall(Node):
    haystack: Node
    needle: Node


@dataclass
class SubstrCall(Node):
    string: Node
    start: Node
    length: Node


@dataclass
class ArrayAddCall(Node):
    array: Node
    value: Node


@dataclass
class ArrayRemoveCall(Node):
    array: Node
    index: Node


@dataclass
class SqrtCall(Node):
    arg: Node


@dataclass
class AbsCall(Node):
    arg: Node


@dataclass
class RandomCall(Node):
    arg: Node


@dataclass
class RoundCall(Node):
    arg: Node


@dataclass
class UpperCall(Node):
    arg: Node


@dataclass
class LowerCall(Node):
    arg: Node


@dataclass
class ReplaceCall(Node):
    string: Node
    old: Node
    new: Node


@dataclass
class SplitCall(Node):
    string: Node
    separator: Node


@dataclass
class JoinCall(Node):
    array: Node
    separator: Node


@dataclass
class StartsCall(Node):
    string: Node
    prefix: Node


@dataclass
class EndsCall(Node):
    string: Node
    suffix: Node


@dataclass
class ReverseCall(Node):
    arg: Node


@dataclass
class InputExpr(Node):
    pass


@dataclass
class PrintStmt(Node):
    expr: Node


@dataclass
class CallExpr(Node):
    name: str
    args: list


@dataclass
class CallStmt(Node):
    name: str
    args: list


@dataclass
class AssignStmt(Node):
    target: Union[str, IndexGet, MemberGet]
    expr: Node
    is_declaration: bool = False


@dataclass
class IfStmt(Node):
    branches: list  # [(условие, тело: list), ...]
    else_body: list


@dataclass
class WhileStmt(Node):
    cond: Node
    body: list


@dataclass
class ForStmt(Node):
    var: str
    start: Node
    end: Node
    body: list


@dataclass
class RepeatStmt(Node):
    count: Node
    body: list


@dataclass
class ProcDef(Node):
    name: str
    params: list
    body: list


@dataclass
class ReturnStmt(Node):
    expr: Node | None


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


Program = list[Node]

Expr = Union[
    Number, String, Char, Bool, Null, Variable, Array, Object,
    UnaryNeg, UnaryNot, BinOp, IndexGet, MemberGet, LengthCall,
    CodeCall, ChrCall, FindCall, SubstrCall, ArrayAddCall,
    ArrayRemoveCall, SqrtCall, AbsCall, RandomCall, RoundCall,
    UpperCall, LowerCall, ReplaceCall, SplitCall, JoinCall,
    StartsCall, EndsCall, ReverseCall,
    InputExpr, CallExpr,
]
Stmt = Union[
    PrintStmt, CallStmt, AssignStmt, IfStmt, WhileStmt, ForStmt,
    RepeatStmt, ProcDef, ReturnStmt, BreakStmt, ContinueStmt,
]