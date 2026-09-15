"""Интерпретатор lu-lang: выполняет программу из узлов AST."""

import math
import random

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
    FindCall,
    ForStmt,
    IfStmt,
    IndexGet,
    InputExpr,
    JoinCall,
    LengthCall,
    LowerCall,
    MemberGet,
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
    UnaryNeg,
    UnaryNot,
    UpperCall,
    Variable,
    WhileStmt,
)

_LOOP_LIMIT = 1_000_000
_RECURSION_LIMIT = 200


class LuLangError(Exception):
    """Ошибка исполнения lu-lang. Сообщение — по-русски и по-дружески."""


class _Return(Exception):
    """Сигнал: процедура закончилась по команде «вернуть»."""

    def __init__(self, value):
        super().__init__()
        self.value = value


class _Break(Exception):
    """Сигнал: выход из цикла по команде «прервать»."""


class _Continue(Exception):
    """Сигнал: переход к следующей итерации цикла по команде «продолжить»."""


class Interpreter:
    """Выполняет программу слева направо, сверху вниз."""

    def __init__(self):
        # Стек областей видимости: снизу глобальная, сверху — локальные.
        self.frames = [{}]
        # Процедуры: имя -> ProcDef.
        self.procs: dict[str, ProcDef] = {}

    def run(self, program):
        try:
            for stmt in program:
                self.execute(stmt)
        except _Return:
            raise LuLangError("«вернуть» можно использовать только внутри процедуры")
        except _Break:
            raise LuLangError("«прервать» можно использовать только внутри цикла")
        except _Continue:
            raise LuLangError("«продолжить» можно использовать только внутри цикла")

    # --- инструкции -------------------------------------------------------

    def execute(self, stmt):
        if isinstance(stmt, PrintStmt):
            print(self._format(self.eval(stmt.expr)))
        elif isinstance(stmt, AssignStmt):
            self._assign(stmt.target, self.eval(stmt.expr), stmt.is_declaration)
        elif isinstance(stmt, CallStmt):
            self._call(stmt.name, stmt.args)
        elif isinstance(stmt, ArrayAddCall):
            self._array_add(self.eval(stmt.array), self.eval(stmt.value))
        elif isinstance(stmt, ArrayRemoveCall):
            self._array_remove(self.eval(stmt.array), self.eval(stmt.index))
        elif isinstance(stmt, IfStmt):
            self._if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._while(stmt)
        elif isinstance(stmt, ForStmt):
            self._for(stmt)
        elif isinstance(stmt, RepeatStmt):
            self._repeat(stmt)
        elif isinstance(stmt, ProcDef):
            self.procs[stmt.name] = stmt
        elif isinstance(stmt, ReturnStmt):
            value = Null() if stmt.expr is None else self.eval(stmt.expr)
            raise _Return(value)
        elif isinstance(stmt, BreakStmt):
            raise _Break()
        elif isinstance(stmt, ContinueStmt):
            raise _Continue()
        else:  # pragma: no cover
            raise LuLangError(f"Не знаю, что делать с такой командой: {stmt!r}")

    def _if(self, stmt):
        for cond, body in stmt.branches:
            if self._truthy(self.eval(cond)):
                self._run_block(body)
                return
        self._run_block(stmt.else_body)

    def _while(self, stmt):
        count = 0
        while self._truthy(self.eval(stmt.cond)):
            try:
                self._run_block(stmt.body)
            except _Break:
                break
            except _Continue:
                continue
            count += 1
            if count > _LOOP_LIMIT:
                raise LuLangError("Похоже, цикл «пока» не может остановиться")

    def _for(self, stmt):
        start = self._as_int(self.eval(stmt.start))
        end = self._as_int(self.eval(stmt.end))
        if start > end:
            return
        count = 0
        for value in range(start, end + 1):
            self._set_var(stmt.var, float(value), is_declaration=True)
            try:
                self._run_block(stmt.body)
            except _Break:
                break
            except _Continue:
                continue
            count += 1
            if count > _LOOP_LIMIT:
                raise LuLangError("Похоже, цикл «для» не может остановиться")

    def _repeat(self, stmt):
        total = self._as_int(self.eval(stmt.count))
        if total > _LOOP_LIMIT:
            raise LuLangError("Столько повторений не сделать — похоже, тут ошибка")
        for _ in range(total):
            try:
                self._run_block(stmt.body)
            except _Break:
                break
            except _Continue:
                continue

    # --- выражения --------------------------------------------------------

    def eval(self, node):
        if isinstance(node, Number):
            return node.value
        if isinstance(node, String):
            return node.value
        if isinstance(node, Char):
            return node.value
        if isinstance(node, Bool):
            return node.value
        if isinstance(node, Null):
            return None
        if isinstance(node, Variable):
            return self._get_var(node.name)
        if isinstance(node, Array):
            return [self.eval(item) for item in node.items]
        if isinstance(node, Object):
            return {key: self.eval(v) for key, v in node.fields.items()}
        if isinstance(node, UnaryNeg):
            return -self.eval(node.operand)
        if isinstance(node, UnaryNot):
            return not self._truthy(self.eval(node.operand))
        if isinstance(node, BinOp):
            if node.op in ("и", "или"):  # узлы нужны для короткого замыкания
                return self._binary(node.op, node.left, node.right)
            return self._binary(node.op, self.eval(node.left), self.eval(node.right))
        if isinstance(node, IndexGet):
            return self._index_get(self.eval(node.obj), self.eval(node.index))
        if isinstance(node, MemberGet):
            return self._member_get(self.eval(node.obj), node.name)
        if isinstance(node, LengthCall):
            return self._length(self.eval(node.arg))
        if isinstance(node, CodeCall):
            return self._code(self.eval(node.arg))
        if isinstance(node, ChrCall):
            return self._chr(self.eval(node.arg))
        if isinstance(node, FindCall):
            return self._find(self.eval(node.haystack), self.eval(node.needle))
        if isinstance(node, SubstrCall):
            return self._substr(self.eval(node.string), self.eval(node.start), self.eval(node.length))
        if isinstance(node, ArrayAddCall):
            return self._array_add(self.eval(node.array), self.eval(node.value))
        if isinstance(node, ArrayRemoveCall):
            return self._array_remove(self.eval(node.array), self.eval(node.index))
        if isinstance(node, SqrtCall):
            return self._sqrt(self.eval(node.arg))
        if isinstance(node, AbsCall):
            return self._abs(self.eval(node.arg))
        if isinstance(node, RandomCall):
            return self._random(self.eval(node.arg))
        if isinstance(node, RoundCall):
            return self._round(self.eval(node.arg))
        if isinstance(node, UpperCall):
            return self._upper(self.eval(node.arg))
        if isinstance(node, LowerCall):
            return self._lower(self.eval(node.arg))
        if isinstance(node, ReplaceCall):
            return self._replace(self.eval(node.string), self.eval(node.old), self.eval(node.new))
        if isinstance(node, SplitCall):
            return self._split(self.eval(node.string), self.eval(node.separator))
        if isinstance(node, JoinCall):
            return self._join(self.eval(node.array), self.eval(node.separator))
        if isinstance(node, StartsCall):
            return self._starts(self.eval(node.string), self.eval(node.prefix))
        if isinstance(node, EndsCall):
            return self._ends(self.eval(node.string), self.eval(node.suffix))
        if isinstance(node, ReverseCall):
            return self._reverse(self.eval(node.arg))
        if isinstance(node, InputExpr):
            return self._read_input()
        if isinstance(node, CallExpr):
            return self._call(node.name, node.args)
        raise LuLangError(f"Не понимаю выражение: {node!r}")

    def _binary(self, op, left, right):
        if op == "и":
            if not self._truthy(self.eval(left)):  # короткое замыкание
                return False
            return self._truthy(self.eval(right))
        if op == "или":
            if self._truthy(self.eval(left)):  # короткое замыкание
                return True
            return self._truthy(self.eval(right))

        if isinstance(left, str) or isinstance(right, str):
            if op == "+":
                return self._format(left) + self._format(right)
            if op in ("=", "!="):
                return (self._format(left) == self._format(right)) if op == "=" else self._format(left) != self._format(right)
            if op in ("<", ">", "<=", ">=") and isinstance(left, str) and isinstance(right, str):
                return _compare_str(op, left, right)
            raise LuLangError("Строки можно только складывать «+»")

        if op in ("=", "!="):
            equal = _equal(left, right)
            return equal if op == "=" else not equal

        if op in ("<", ">", "<=", ">="):
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return _compare_num(op, left, right)
            raise LuLangError("Сравнивать можно только числа или строки")

        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right
        except ZeroDivisionError:
            raise LuLangError("На ноль делить нельзя!")
        raise LuLangError(f"Не знаю такую операцию: {op}")

    def _assign(self, target, value, is_declaration=False):
        if isinstance(target, str):
            self._set_var(target, value, is_declaration)
        elif isinstance(target, MemberGet):
            obj = self.eval(target.obj)
            if not isinstance(obj, dict):
                raise LuLangError("Точку можно ставить только после объекта")
            obj[target.name] = value
        elif isinstance(target, IndexGet):
            self._index_set(self.eval(target.obj), self.eval(target.index), value)

    def _call(self, name, args):
        proc = self.procs.get(name)
        if proc is None:
            raise LuLangError(f"Не знаю такую процедуру: «{name}»")
        if len(args) != len(proc.params):
            raise LuLangError(
                f"Процедуре «{name}» нужно {len(proc.params)} аргументов, а дали {len(args)}"
            )
        if len(self.frames) >= _RECURSION_LIMIT:
            raise LuLangError("Слишком много вложенных вызовов — возможно, бесконечная рекурсия")
        values = [self.eval(arg) for arg in args]
        frame = dict(zip(proc.params, values))
        self.frames.append(frame)
        try:
            self._run_block(proc.body)
        except _Return as signal:
            return signal.value
        finally:
            self.frames.pop()
        return None

    # --- вспомогательное --------------------------------------------------

    def _run_block(self, stmts):
        for stmt in stmts:
            self.execute(stmt)

    def _get_var(self, name):
        for frame in reversed(self.frames):
            if name in frame:
                return frame[name]
        raise LuLangError(f"Я ещё не знаю, что такое «{name}»")

    def _set_var(self, name, value, is_declaration=False):
        if is_declaration:
            self.frames[-1][name] = value
            return
        for frame in reversed(self.frames):
            if name in frame:
                frame[name] = value
                return
        self.frames[0][name] = value

    def _index_get(self, obj, index):
        if not isinstance(obj, (list, str)):
            raise LuLangError("Квадратные скобки работают только с массивами и строками")
        i = self._as_int(index)
        if not 0 <= i < len(obj):
            raise LuLangError(f"В массиве или строке нет элемента с номером {i}")
        return obj[i]

    def _index_set(self, obj, index, value):
        if not isinstance(obj, list):
            raise LuLangError("Квадратные скобки работают только с массивами")
        i = self._as_int(index)
        if not 0 <= i < len(obj):
            raise LuLangError(f"В массиве нет элемента с номером {i}")
        obj[i] = value

    def _member_get(self, obj, name):
        if not isinstance(obj, dict):
            raise LuLangError("Точку можно ставить только после объекта")
        if name not in obj:
            raise LuLangError(f"У объекта нет поля «{name}»")
        return obj[name]

    def _length(self, obj):
        if isinstance(obj, (list, dict, str)):
            return float(len(obj))
        raise LuLangError("«длина» работает только с массивами, строками и объектами")

    def _code(self, obj):
        if isinstance(obj, str) and len(obj) == 1:
            return float(ord(obj))
        raise LuLangError("«код» работает только с одним символом")

    def _chr(self, obj):
        if isinstance(obj, bool):
            raise LuLangError("«символ» ожидает число, а не булево значение")
        if isinstance(obj, (int, float)):
            code = int(obj)
            if 0 <= code <= 0x10FFFF:
                return chr(code)
            raise LuLangError(f"Нет символа с кодом {code}")
        raise LuLangError("«символ» ожидает число — код символа в Юникоде")

    def _find(self, haystack, needle):
        if isinstance(haystack, str) and isinstance(needle, str):
            return float(haystack.find(needle))
        raise LuLangError("«найти» работает только со строками")

    def _substr(self, s, start, length):
        if not isinstance(s, str):
            raise LuLangError("«подстрока» работает только со строками")
        i = self._as_int(start)
        n = self._as_int(length)
        if i < 0 or i >= len(s):
            return ""
        return s[i:i + n]

    def _array_add(self, arr, val):
        if not isinstance(arr, list):
            raise LuLangError("«добавить» работает только с массивами")
        arr.append(val)
        return arr

    def _array_remove(self, arr, index):
        if not isinstance(arr, list):
            raise LuLangError("«удалить» работает только с массивами")
        i = self._as_int(index)
        if not 0 <= i < len(arr):
            raise LuLangError(f"В массиве нет элемента с номером {i}")
        del arr[i]
        return arr

    def _sqrt(self, x):
        if isinstance(x, bool):
            raise LuLangError("«корень» ожидает число")
        if isinstance(x, (int, float)):
            if x < 0:
                raise LuLangError("Нельзя взять корень из отрицательного числа")
            return math.sqrt(x)
        raise LuLangError("«корень» ожидает число")

    def _abs(self, x):
        if isinstance(x, (int, float)):
            return float(abs(x))
        raise LuLangError("«модуль» ожидает число")

    def _random(self, x):
        if isinstance(x, bool):
            raise LuLangError("«случ» ожидает число")
        if isinstance(x, (int, float)):
            n = int(x)
            if n <= 0:
                raise LuLangError("«случ» ожидает положительное число")
            return float(random.randrange(n))
        raise LuLangError("«случ» ожидает число")

    def _round(self, x):
        if isinstance(x, (int, float)):
            return float(round(x))
        raise LuLangError("«округлить» ожидает число")

    def _upper(self, s):
        if isinstance(s, str):
            return s.upper()
        raise LuLangError("«вверх» работает только со строками")

    def _lower(self, s):
        if isinstance(s, str):
            return s.lower()
        raise LuLangError("«вниз» работает только со строками")

    def _replace(self, s, old, new):
        if isinstance(s, str) and isinstance(old, str) and isinstance(new, str):
            return s.replace(old, new)
        raise LuLangError("«заменить» работает только со строками")

    def _split(self, s, sep):
        if isinstance(s, str) and isinstance(sep, str):
            return s.split(sep)
        raise LuLangError("«разделить» работает только со строками")

    def _join(self, arr, sep):
        if isinstance(arr, list) and isinstance(sep, str):
            return sep.join(str(self._format(x)) for x in arr)
        raise LuLangError("«соединить» ожидает массив и строку-разделитель")

    def _starts(self, s, prefix):
        if isinstance(s, str) and isinstance(prefix, str):
            return s.startswith(prefix)
        raise LuLangError("«начинается» работает только со строками")

    def _ends(self, s, suffix):
        if isinstance(s, str) and isinstance(suffix, str):
            return s.endswith(suffix)
        raise LuLangError("«заканчивается» работает только со строками")

    def _reverse(self, s):
        if isinstance(s, str):
            return s[::-1]
        raise LuLangError("«перевернуть» работает только со строками")

    def _read_input(self):
        text = input().strip()
        try:
            if "." in text or "," in text:
                return float(text.replace(",", "."))
            return int(text)
        except ValueError:
            return text

    @staticmethod
    def _as_int(value):
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, (int, float)):
            return int(value)
        raise LuLangError("Нужно число, а получилось что-то другое")

    @staticmethod
    def _truthy(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    @staticmethod
    def _format(value):
        # 10.0 печатаем как 10 — так понятнее ребёнку.
        if isinstance(value, bool):
            return "истина" if value else "ложь"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if value is None:
            return "ничего"
        if isinstance(value, list):
            return "[" + ", ".join(Interpreter._format(x) for x in value) + "]"
        if isinstance(value, dict):
            body = ", ".join(f"{k}: {Interpreter._format(v)}" for k, v in value.items())
            return "{" + body + "}"
        return str(value)


def _compare_num(op, left, right):
    return {
        "<": left < right,
        ">": left > right,
        "<=": left <= right,
        ">=": left >= right,
    }[op]


def _compare_str(op, left, right):
    return {
        "<": left < right,
        ">": left > right,
        "<=": left <= right,
        ">=": left >= right,
    }[op]


def _equal(left, right):
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    return left == right