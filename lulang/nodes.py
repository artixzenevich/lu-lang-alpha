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


Program = list[Node]

Expr = Union[
    Number, String, Char, Bool, Null, Variable, Array, Object,
    UnaryNeg, UnaryNot, BinOp, IndexGet, MemberGet, LengthCall,
    CodeCall, ChrCall, InputExpr, CallExpr,
]
Stmt = Union[
    PrintStmt, CallStmt, AssignStmt, IfStmt, WhileStmt, ForStmt,
    RepeatStmt, ProcDef, ReturnStmt,
]