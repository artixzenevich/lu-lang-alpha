"""Грамматика языка lu-lang на Lark.

Поддерживаются:
    Команды:          печать(), запомнить, переназначение, ввод(), вызов() процедуры.
    Ветвление:        если / то / иначе / иначе если / конец.
    Циклы:            пока, для .. от .. до .., повтори .. раз.
    Процедуры:        процедура, выполнить(), вернуть.
    Типы:             числа, строки, символы, истина/ложь, ничего,
                      массивы [..], объекты {имя: ..}.
    Операторы:        + - * /, сравнения = != < > <= >=, и/или/не.
    Комментарии:      //, # (однострочные), /// ... /// (многострочные).
"""

from collections import Counter

from lark import Lark, Token, Tree

# Ключевые слова запрещены внутри имён переменных с помощью
# отрицательного просмотра вперёд в NAME.
_KEYWORDS = (
    "печать|запомнить|ввод|если|то|иначе|конец|и|или|не|для|от|до|"
    "пока|повтори|раз|процедура|выполнить|вернуть|истина|ложь|ничего|"
    "длина|код|символ|найти|подстрока|добавить|удалить|корень|модуль|"
    "случ|округлить|вверх|вниз|заменить|разделить|соединить|начинается|"
    "заканчивается|перевернуть|прервать|продолжить"
)

GRAMMAR = r"""
start: stmt*

?stmt: print_stmt
     | call_stmt
     | assign_stmt
     | if_stmt
     | while_stmt
     | for_stmt
     | repeat_stmt
     | proc_def
     | return_stmt
     | break_stmt
     | continue_stmt
     | array_add_stmt
     | array_remove_stmt
     | empty_stmt

print_stmt: PRINT "(" expr ")"
call_stmt: CALL NAME "(" arglist? ")"
assign_stmt: LET NAME "=" expr
           | lvalue "=" expr
lvalue: NAME | NAME "." NAME | NAME "[" expr "]"

if_stmt: IF expr THEN stmts elif_part* else_part? END
elif_part: ELSE IF expr THEN stmts
else_part: ELSE stmts

while_stmt: WHILE expr stmts END
for_stmt: FOR NAME FROM expr TO expr stmts END
repeat_stmt: REPEAT expr TIMES stmts END
proc_def: PROC NAME "(" params? ")" stmts END
params: NAME ("," NAME)*
return_stmt: RETURN expr?
break_stmt: BREAK
continue_stmt: CONTINUE
empty_stmt: NEWLINE
array_add_stmt: ARRAY_ADD "(" expr "," expr ")"
array_remove_stmt: ARRAY_REMOVE "(" expr "," expr ")"

stmts: stmt*

// Вызовы процедур обрамляются круглыми скобками, поэтому неоднозначности
// «жадных» аргументов нет — скобка четко обозначает конец вызова.
// Пример: "1 + 2" в
//    печать("x -> " + выполнить плюс_один(1 + 2))
// целиком попадает в аргумент (3 -> 4), а не в конкатенацию ("22").
// Выражение в скобках:
//    печать(выполнить плюс_один(1) + 2)
?expr: call_expr
     | neg_call_expr
     | not_call_expr
     | call_tail_expr

neg_call_expr: "-" call_expr -> neg
not_call_expr: NOT call_expr -> not_op

call_tail_expr: expr_no_call (BINOP call_expr)?

?expr_no_call: or_expr
?or_expr: and_expr (OR and_expr)*
?and_expr: not_expr (AND not_expr)*
?not_expr: NOT not_expr -> not_op
         | comparison
comparison: additive (comparison_op additive)?
?additive: multiplicative (("+" | "-") multiplicative)*
?multiplicative: unary_expr (("*" | "/") unary_expr)*
?unary_expr: "-" unary_expr -> neg
           | postfix_expr
?postfix_expr: atom
              | postfix_expr "[" expr "]" -> index_get
              | postfix_expr "." NAME -> member_get

?atom: NUMBER           -> number
     | STRING           -> string
     | CHAR             -> char
     | TRUE             -> true
     | FALSE            -> false
     | NULL             -> null
     | NAME             -> variable
     | array_literal
     | object_literal
| LENGTH "(" expr ")" -> length_call
      | CODE "(" expr ")" -> code_call
      | CHR "(" expr ")" -> chr_call
      | FIND "(" expr "," expr ")" -> find_call
      | SUBSTR "(" expr "," expr "," expr ")" -> substr_call
      | ARRAY_ADD "(" expr "," expr ")" -> array_add_call
      | ARRAY_REMOVE "(" expr "," expr ")" -> array_remove_call
      | SQRT "(" expr ")" -> sqrt_call
      | ABS "(" expr ")" -> abs_call
      | RANDOM "(" expr ")" -> random_call
      | ROUND "(" expr ")" -> round_call
      | UPPER "(" expr ")" -> upper_call
      | LOWER "(" expr ")" -> lower_call
      | REPLACE "(" expr "," expr "," expr ")" -> replace_call
      | SPLIT "(" expr "," expr ")" -> split_call
      | JOIN "(" expr "," expr ")" -> join_call
      | STARTS "(" expr "," expr ")" -> starts_call
      | ENDS "(" expr "," expr ")" -> ends_call
      | REVERSE "(" expr ")" -> reverse_call
      | INPUT "(" ")" -> input
     | "(" expr ")"

call_expr: CALL NAME "(" arglist? ")"

array_literal: "[" (expr ("," expr)*)? "]"
object_literal: "{" (NAME ":" expr ("," NAME ":" expr)*)? "}"

arglist: expr ("," expr)*

?comparison_op: EQ | NE | LT | LE | GT | GE

PRINT: "печать"
LET: "запомнить"
INPUT: "ввод"
CALL: "выполнить"
IF: "если"
THEN: "то"
ELSE: "иначе"
END: "конец"
AND: "и"
OR: "или"
NOT: "не"
FOR: "для"
FROM: "от"
TO: "до"
WHILE: "пока"
REPEAT: "повтори"
TIMES: "раз"
PROC: "процедура"
RETURN: "вернуть"
BREAK: "прервать"
CONTINUE: "продолжить"
TRUE: "истина"
FALSE: "ложь"
NULL: "ничего"
LENGTH: "длина"
CODE: "код"
CHR: "символ"
FIND: "найти"
SUBSTR: "подстрока"
ARRAY_ADD: "добавить"
ARRAY_REMOVE: "удалить"
SQRT: "корень"
ABS: "модуль"
RANDOM: "случ"
ROUND: "округлить"
UPPER: "вверх"
LOWER: "вниз"
REPLACE: "заменить"
SPLIT: "разделить"
JOIN: "соединить"
STARTS: "начинается"
ENDS: "заканчивается"
REVERSE: "перевернуть"

BINOP: "+" | "-" | "*" | "/" | "=" | "!=" | "<" | "<=" | ">" | ">=" | AND | OR

EQ: "="
NE: "!="
LT: "<"
LE: "<="
GT: ">"
GE: ">="
DOT: "."
COMMA: ","

NAME: /(?!(?:""" + _KEYWORDS + r""")\b)[^\W\d][\w]*/
NUMBER: INT | FLOAT
STRING: /"[^"\n]*"/
CHAR: /'[^'\n]'/

%import common.INT
%import common.FLOAT
%import common.NEWLINE
%import common.WS_INLINE

%ignore /\/\/(?!\/)[^\n]*/
%ignore /\/\/\/[\s\S]*?\/\/\//
%ignore /#[^\n]*/
%ignore WS_INLINE
"""


def _build():
    return Lark(
        GRAMMAR,
        parser="earley",
        propagate_positions=True,
        keep_all_tokens=True,
        ambiguity="explicit",
    )


_parser = _build()


def _arglists(tree):
    return [sub for sub in tree.iter_subtrees() if sub.data == "arglist"]


def _returns_with_expr(tree):
    """Сколько команд «вернуть» имеют значение-выражение."""
    count = 0
    for sub in tree.iter_subtrees():
        if sub.data == "return_stmt" and any(
            not isinstance(child, Token) for child in sub.children[1:]
        ):
            count += 1
    return count


def _resolve(node):
    """Раскрыть неоднозначности. Выбираем вариант, где
    «вернуть» предпочитает значение. Оставшиеся неоднозначности лексера
    (например, слово «или» можно прочитать как два токена «и» + «ли»)
    решаем в пользу варианта, где на одной строке остаётся одна инструкция.
    Счёт только по тем местам, где варианты реально отличаются, чтобы
    один файл не «перетягивал» другой."""
    if isinstance(node, Token):
        return node
    if node.data == "_ambig":
        return _pick(_resolve(child) for child in node.children)
    return Tree(node.data, [_resolve(child) for child in node.children])


def _total_arg_tokens(tree):
    return sum(
        len(list(a.scan_values(lambda t: isinstance(t, Token))))
        for a in _arglists(tree)
    )


_STMT_TYPES = frozenset(
    {
        "print_stmt",
        "call_stmt",
        "assign_stmt",
        "if_stmt",
        "while_stmt",
        "for_stmt",
        "repeat_stmt",
        "proc_def",
        "return_stmt",
        "break_stmt",
        "continue_stmt",
    }
)


def _stmt_count(tree):
    """Сколько инструкций в этом варианте разбора."""
    return sum(1 for sub in tree.iter_subtrees() if sub.data in _STMT_TYPES)


def _pick(parses):
    parses = list(parses)
    # Lark хранит варианты в set — порядок случаен. Сначала сортируем,
    # чтобы результат был воспроизводимым.
    parses.sort(key=lambda t: repr(t))
    # Аргументы-«общие» для всех вариантов одинаковы — их игнорируем.
    hashes = Counter()
    for tree in parses:
        hashes.update(Counter(repr(a) for a in _arglists(tree)))
    n = len(parses)
    unique = {h for h, c in hashes.items() if c < n}

    def local_score(tree):
        bonus = 0
        for a in _arglists(tree):
            if repr(a) in unique:
                bonus += len(list(a.scan_values(lambda t: isinstance(t, Token))))
        return bonus

    # Вариант, где на строке меньше инструкций (то есть слово «или»
    # не «располовинилось» на «и» + переменную «ли»).
    # Затем «вернуть» со значением, а напоследок — больше аргументов
    # в сумме (просто чтобы выбор был стабильным).
    return max(
        parses,
        key=lambda t: (
            -_stmt_count(t),
            _returns_with_expr(t),
            _total_arg_tokens(t),
        ),
    )


def parse(source: str):
    """Разобрать исходник языка lu-lang в дерево Lark."""
    tree = _parser.parse(source)
    return _resolve(tree)