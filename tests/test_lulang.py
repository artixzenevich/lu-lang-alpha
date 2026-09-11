"""Тесты lu-lang: парсер и интерпретатор."""

import pytest

from lulang.ast_builder import build_ast
from lulang.grammar import parse
from lulang.interpreter import Interpreter, LuLangError
from lulang.nodes import AssignStmt, BinOp, PrintStmt


def run(source: str, capsys) -> str:
    """Выполнить исходник и вернуть весь stdout."""
    program = build_ast(parse(source))
    Interpreter().run(program)
    return capsys.readouterr().out


def test_parse_and_build_ast():
    program = build_ast(parse("запомнить x = 2 + 3"))
    assert len(program) == 1
    stmt = program[0]
    assert isinstance(stmt, AssignStmt)
    assert stmt.target == "x"
    assert isinstance(stmt.expr, BinOp)
    assert stmt.expr.op == "+"


def test_print_with_colon(capsys):
    out = run("печать: 42\n", capsys)
    assert out == "42\n"


def test_print_and_math(capsys):
    out = run("печать: (2 + 3) * 4\nпечать: 100 / 4\nпечать: -5 + 12\n", capsys)
    assert out == "20\n25\n7\n"


def test_string_concatenation(capsys):
    out = run('печать: "Привет, " + "мир"\n', capsys)
    assert out == "Привет, мир\n"


def test_variables(capsys):
    out = run(
        'запомнить имя = "Лу"\n'
        "запомнить n = 5\n"
        "печать: имя\n"
        "печать: n * 2\n",
        capsys,
    )
    assert out == "Лу\n10\n"


def test_reassign_variable(capsys):
    out = run("запомнить x = 10\nx = x - 1\nx = x - 1\nпечать: x\n", capsys)
    assert out == "8\n"


def test_keywords_are_reserved():
    from lark import LarkError

    for keyword in ("печать", "запомнить", "если", "конец"):
        with pytest.raises(LarkError):
            parse(f"запомнить {keyword} = 1")


def test_comment_styles(capsys):
    out = run(
        '// однострочный// комментарий\n'
        "#'# тоже \n"
        "/// многострочный\nкомментарий ///\n"
        'печать: "ок"\n',
        capsys,
    )
    assert out == "ок\n"


def test_unknown_variable_raises():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать: чего_то_там")))


def test_division_by_zero_raises():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать: 1 / 0")))


@pytest.mark.parametrize(
    "source",
    [
        "печать",  # после печать обязательно :
        "запомнить = 5",
        "печать: 2 +",
        "печать: (2 + 3",
        "запомнить x 5",
        "если x то",
    ],
)
def test_syntax_errors(source):
    from lark import LarkError

    with pytest.raises(LarkError):
        parse(source)


# --- булево, сравнения, логика -------------------------------------------


@pytest.mark.parametrize(
    "source,expected",
    [
        ("печать: истина", "истина\n"),
        ("печать: ложь", "ложь\n"),
        ("печать: 5 = 5", "истина\n"),
        ("печать: 5 != 5", "ложь\n"),
        ("печать: 3 < 5", "истина\n"),
        ("печать: 3 > 5", "ложь\n"),
        ("печать: 3 <= 3", "истина\n"),
        ("печать: 4 >= 5", "ложь\n"),
        ('печать: "а" < "б"', "истина\n"),
        ("печать: 1 = 2 или 2 = 2", "истина\n"),
        ("печать: 1 = 2 и 2 = 2", "ложь\n"),
        ("печать: не ложь", "истина\n"),
    ],
)
def test_booleans_and_comparisons(capsys, source, expected):
    assert run(source + "\n", capsys) == expected


def test_and_or_with_call_not_split(capsys):
    # «или» должно оставаться одним словом, а не распадаться на «и» + «ли»
    # в соседнюю инструкцию:  ложь или выполнить да  =>  истина
    out = run(
        "процедура да:\n    вернуть истина\nконец\n"
        "печать: ложь или выполнить да\n"
        "печать: истина и выполнить да\n",
        capsys,
    )
    assert out == "истина\nистина\n"


def test_and_short_circuit(capsys):
    out = run("печать: ложь и 1 / 0 = 1\n", capsys)
    assert out == "ложь\n"


def test_nothing(capsys):
    out = run("запомнить x = ничего\nпечать: x\n", capsys)
    assert out == "ничего\n"


def test_char(capsys):
    out = run("печать: 'Л'\nпечать: 'а'\n", capsys)
    assert out == "Л\nа\n"


# --- условия --------------------------------------------------------------


def test_if_else(capsys):
    out = run(
        "запомнить возраст = 5\n"
        'если возраст > 5 то\n    печать: "большой"\n'
        'иначе если возраст = 5 то\n    печать: "ровно пять"\n'
        'иначе\n    печать: "малыш"\n'
        "конец\n",
        capsys,
    )
    assert out == "ровно пять\n"


def test_if_without_else(capsys):
    out = run("если 1 < 2 то\n    печать: \"да\"\nконец\n", capsys)
    assert out == "да\n"


def test_nested_if_and_elseif(capsys):
    out = run(
        "запомнить a = 2\n"
        'если a > 5 то\n    печать: "A"\n'
        'иначе если a = 2 то\n    печать: "B"\n'
        "иначе\n"
        "    если a = 3 то\n        печать: \"C\"\n"
        "    конец\n"
        "конец\n",
        capsys,
    )
    assert out == "B\n"


# --- циклы ----------------------------------------------------------------


def test_for_loop(capsys):
    out = run('для i от 1 до 5\n    печать: "Шаг " + i\nконец\n', capsys)
    assert out == "Шаг 1\nШаг 2\nШаг 3\nШаг 4\nШаг 5\n"


def test_for_loop_descending_skipped(capsys):
    out = run("для i от 5 до 1\n    печать: i\nконец\n", capsys)
    assert out == ""


def test_while_loop(capsys):
    out = run(
        "запомнить x = 3\n"
        "пока x > 0\n    печать: x\n    x = x - 1\n"
        "конец\n",
        capsys,
    )
    assert out == "3\n2\n1\n"


def test_repeat_loop(capsys):
    out = run('повтори 3 раз\n    печать: "Мяу!"\nконец\n', capsys)
    assert out == "Мяу!\nМяу!\nМяу!\n"


def test_infinite_loop_guard():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("пока истина\n    печать: 1\nконец")))


# --- процедуры ------------------------------------------------------------


def test_procedure_with_return(capsys):
    out = run(
        "процедура квадрат: число\n"
        "    вернуть число * число\n"
        "конец\n"
        "запомнить x = выполнить квадрат: 5\n"
        "печать: x\n",
        capsys,
    )
    assert out == "25\n"


def test_procedure_call_statement(capsys):
    out = run(
        "процедура привет: имя, возраст\n"
        '    печать: "Привет, " + имя + ", тебе " + возраст + " лет."\n'
        "конец\n"
        'выполнить привет: "Лу", 5\n',
        capsys,
    )
    assert out == "Привет, Лу, тебе 5 лет.\n"


def test_factorial_recursion(capsys):
    out = run(
        "процедура факториал: k\n"
        "    если k <= 1 то\n        вернуть 1\n    конец\n"
        "    вернуть k * выполнить факториал: k - 1\n"
        "конец\n"
        "печать: выполнить факториал: 5\n",
        capsys,
    )
    assert out == "120\n"


def test_call_args_greedy(capsys):
    out = run(
        "процедура плюс: a, b\n    вернуть a + b\nконец\n"
        "печать: выполнить плюс: 1, 2\n",
        capsys,
    )
    assert out == "3\n"


def test_procedure_without_params(capsys):
    # Процедура без параметров вызывается и без аргументов,
    # причём двоеточие после имени вызова допустимо.
    out = run(
        "процедура привет:\n"
        '    печать: "Привет"\n'
        "конец\n"
        "процедура пять:\n"
        "    вернуть 5\n"
        "конец\n"
        "выполнить привет:\n"
        'печать: "Число: " + выполнить пять:\n',
        capsys,
    )
    assert out == "Привет\nЧисло: 5\n"


def test_call_argument_with_arithmetic(capsys):
    # Внутри вызова арифметика относится к аргументу, а не считается после вызова.
    out = run(
        "процедура плюс_один: a\n    вернуть a + 1\nконец\n"
        "печать: выполнить плюс_один: 1 + 2\n",
        capsys,
    )
    assert out == "4\n"


def test_procedure_wrong_arg_count():
    src = "процедура о: a\n    вернуть a\nконец\nпечать: выполнить о: 1, 2\n"
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse(src)))


def test_unknown_procedure():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("выполнить незнакомую: 1")))


def test_infinite_recursion_guard():
    with pytest.raises(LuLangError):
        Interpreter().run(
            build_ast(
                parse(
                    "процедура вечность: x\n    вернуть выполнить вечность: x\nконец\n"
                    "печать: выполнить вечность: 1\n"
                )
            )
        )


# --- массивы и объекты ----------------------------------------------------


def test_array_literals(capsys):
    out = run(
        'запомнить фрукты = ["яблоко", "груша", "слива"]\n'
        "печать: фрукты[0]\n"
        'фрукты[1] = "банан"\n'
        "печать: фрукты\n"
        "печать: длина(фрукты)\n",
        capsys,
    )
    assert out == "яблоко\n[яблоко, банан, слива]\n3\n"


def test_empty_array(capsys):
    out = run("запомнить пусто = []\nпечать: длина(пусто)\n", capsys)
    assert out == "0\n"


def test_array_index_out_of_range():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse('запомнить a = [1]\nпечать: a[5]')))


def test_object_literals(capsys):
    out = run(
        'запомнить кот = {имя: "Лу", возраст: 5}\n'
        "печать: кот.имя\n"
        "кот.возраст = 6\n"
        'кот.цвет = "рыжий"\n'
        "печать: кот.возраст\n"
        "печать: кот\n",
        capsys,
    )
    assert out == "Лу\n6\n{имя: Лу, возраст: 6, цвет: рыжий}\n"


def test_object_unknown_field():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("запомнить к = {a: 1}\nпечать: к.b")))


def test_length_on_string(capsys):
    out = run('запомнить s = "привет"\nпечать: длина(s)\n', capsys)
    assert out == "6\n"


# --- ввод ----------------------------------------------------------------


def test_input_number(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "10")
    out = run("запомнить n = ввод:\nпечать: n + 1\n", capsys)
    assert out == "11\n"


def test_input_string(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "Вася")
    out = run("запомнить имя = ввод:\nпечать: имя\n", capsys)
    assert out == "Вася\n"