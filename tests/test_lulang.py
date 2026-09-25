"""Тесты lu-lang: парсер и интерпретатор."""

import pytest
from pathlib import Path

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
    out = run("печать(42)\n", capsys)
    assert out == "42\n"


def test_print_and_math(capsys):
    out = run("печать((2 + 3) * 4)\nпечать(100 / 4)\nпечать(-5 + 12)\n", capsys)
    assert out == "20\n25\n7\n"


def test_string_concatenation(capsys):
    out = run('печать("Привет, " + "мир")\n', capsys)
    assert out == "Привет, мир\n"


def test_variables(capsys):
    out = run(
        'запомнить имя = "Лу"\n'
        "запомнить n = 5\n"
        "печать(имя)\n"
        "печать(n * 2)\n",
        capsys,
    )
    assert out == "Лу\n10\n"


def test_reassign_variable(capsys):
    out = run("запомнить x = 10\nx = x - 1\nx = x - 1\nпечать(x)\n", capsys)
    assert out == "8\n"


def test_keywords_are_reserved():
    from lark import LarkError

    for keyword in (
        "печать",
        "запомнить",
        "если",
        "конец",
        "подключить",
        "как",
        "из",
        "взять",
        "всё",
    ):
        with pytest.raises(LarkError):
            parse(f"запомнить {keyword} = 1")


def test_comment_styles(capsys):
    out = run(
        '// однострочный// комментарий\n'
        "#'# тоже \n"
        "/// многострочный\nкомментарий ///\n"
        'печать("ок")\n',
        capsys,
    )
    assert out == "ок\n"


def test_unknown_variable_raises():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать(чего_то_там)")))


def test_division_by_zero_raises():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать(1 / 0)")))


@pytest.mark.parametrize(
    "source",
    [
        "печать",       # после печать обязательно (
        "печать:",      # двоеточие больше не используется
        "запомнить = 5",
        "печать(2 +",   # незакрытая скобка
        "печать((2 + 3)",  # незакрытая скобка
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
        ("печать(истина)", "истина\n"),
        ("печать(ложь)", "ложь\n"),
        ("печать(5 = 5)", "истина\n"),
        ("печать(5 != 5)", "ложь\n"),
        ("печать(3 < 5)", "истина\n"),
        ("печать(3 > 5)", "ложь\n"),
        ("печать(3 <= 3)", "истина\n"),
        ("печать(4 >= 5)", "ложь\n"),
        ('печать("а" < "б")', "истина\n"),
        ("печать(1 = 2 или 2 = 2)", "истина\n"),
        ("печать(1 = 2 и 2 = 2)", "ложь\n"),
        ("печать(не ложь)", "истина\n"),
    ],
)
def test_booleans_and_comparisons(capsys, source, expected):
    assert run(source + "\n", capsys) == expected


def test_and_or_with_call_not_split(capsys):
    # «или» должно оставаться одним словом, а не распадаться на «и» + «ли»
    # в соседнюю инструкцию:  ложь или выполнить да()  =>  истина
    out = run(
        "процедура да()\n    вернуть истина\nконец\n"
        "печать(ложь или выполнить да())\n"
        "печать(истина и выполнить да())\n",
        capsys,
    )
    assert out == "истина\nистина\n"


def test_and_short_circuit(capsys):
    out = run("печать(ложь и 1 / 0 = 1)\n", capsys)
    assert out == "ложь\n"


def test_nothing(capsys):
    out = run("запомнить x = ничего\nпечать(x)\n", capsys)
    assert out == "ничего\n"


def test_char(capsys):
    out = run("печать('Л')\nпечать('а')\n", capsys)
    assert out == "Л\nа\n"


# --- условия --------------------------------------------------------------


def test_if_else(capsys):
    out = run(
        "запомнить возраст = 5\n"
        'если возраст > 5 то\n    печать("большой")\n'
        'иначе если возраст = 5 то\n    печать("ровно пять")\n'
        'иначе\n    печать("малыш")\n'
        "конец\n",
        capsys,
    )
    assert out == "ровно пять\n"


def test_if_without_else(capsys):
    out = run("если 1 < 2 то\n    печать(\"да\")\nконец\n", capsys)
    assert out == "да\n"


def test_nested_if_and_elseif(capsys):
    out = run(
        "запомнить a = 2\n"
        'если a > 5 то\n    печать("A")\n'
        'иначе если a = 2 то\n    печать("B")\n'
        "иначе\n"
        "    если a = 3 то\n        печать(\"C\")\n"
        "    конец\n"
        "конец\n",
        capsys,
    )
    assert out == "B\n"


# --- циклы ----------------------------------------------------------------


def test_for_loop(capsys):
    out = run('для i от 1 до 5\n    печать("Шаг " + i)\nконец\n', capsys)
    assert out == "Шаг 1\nШаг 2\nШаг 3\nШаг 4\nШаг 5\n"


def test_for_loop_descending_skipped(capsys):
    out = run("для i от 5 до 1\n    печать(i)\nконец\n", capsys)
    assert out == ""


def test_while_loop(capsys):
    out = run(
        "запомнить x = 3\n"
        "пока x > 0\n    печать(x)\n    x = x - 1\n"
        "конец\n",
        capsys,
    )
    assert out == "3\n2\n1\n"


def test_repeat_loop(capsys):
    out = run('повтори 3 раз\n    печать("Мяу!")\nконец\n', capsys)
    assert out == "Мяу!\nМяу!\nМяу!\n"


def test_infinite_loop_guard():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("пока истина\n    печать(1)\nконец")))


def test_break_while(capsys):
    out = run(
        "запомнить x = 3\n"
        "пока x > 0\n"
        "    печать(x)\n"
        "    прервать\n"
        "    печать(\"не_попадём\")\n"
        "    x = x - 1\n"
        "конец\n",
        capsys,
    )
    assert out == "3\n"


def test_continue_while(capsys):
    out = run(
        "запомнить x = 3\n"
        "пока x > 0\n"
        "    x = x - 1\n"
        "    если x = 2 то\n"
        "        продолжить\n"
        "    конец\n"
        "    печать(x)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n0\n"


def test_break_for(capsys):
    out = run(
        "для i от 1 до 5\n"
        "    если i = 3 то\n"
        "        прервать\n"
        "    конец\n"
        "    печать(i)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n2\n"


def test_continue_for(capsys):
    out = run(
        "для i от 1 до 5\n"
        "    если i = 3 то\n"
        "        продолжить\n"
        "    конец\n"
        "    печать(i)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n2\n4\n5\n"


def test_break_repeat(capsys):
    out = run(
        "повтори 10 раз\n"
        "    прервать\n"
        "    печать(\"не_попадём\")\n"
        "конец\n"
        'печать("ок")\n',
        capsys,
    )
    assert out == "ок\n"


def test_continue_repeat(capsys):
    out = run(
        "запомнить x = 0\n"
        "повтори 5 раз\n"
        "    x = x + 1\n"
        "    если x = 3 то\n"
        "        продолжить\n"
        "    конец\n"
        "    печать(x)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n2\n4\n5\n"


def test_break_outside_loop_raises():
    with pytest.raises(LuLangError, match="прервать"):
        Interpreter().run(build_ast(parse("прервать")))


def test_continue_outside_loop_raises():
    with pytest.raises(LuLangError, match="продолжить"):
        Interpreter().run(build_ast(parse("продолжить")))


def test_break_nested_loops(capsys):
    out = run(
        "для i от 1 до 3\n"
        "    прервать\n"
        "    печать(i)\n"
        "конец\n"
        'печать("после_цикла")\n',
        capsys,
    )
    assert out == "после_цикла\n"


# --- процедуры ------------------------------------------------------------


def test_procedure_with_return(capsys):
    out = run(
        "процедура квадрат(число)\n"
        "    вернуть число * число\n"
        "конец\n"
        "запомнить x = выполнить квадрат(5)\n"
        "печать(x)\n",
        capsys,
    )
    assert out == "25\n"


def test_procedure_call_statement(capsys):
    out = run(
        "процедура привет(имя, возраст)\n"
        '    печать("Привет, " + имя + ", тебе " + возраст + " лет.")\n'
        "конец\n"
        'выполнить привет("Лу", 5)\n',
        capsys,
    )
    assert out == "Привет, Лу, тебе 5 лет.\n"


def test_factorial_recursion(capsys):
    out = run(
        "процедура факториал(k)\n"
        "    если k <= 1 то\n        вернуть 1\n    конец\n"
        "    вернуть k * выполнить факториал(k - 1)\n"
        "конец\n"
        "печать(выполнить факториал(5))\n",
        capsys,
    )
    assert out == "120\n"


def test_call_args_greedy(capsys):
    out = run(
        "процедура плюс(a, b)\n    вернуть a + b\nконец\n"
        "печать(выполнить плюс(1, 2))\n",
        capsys,
    )
    assert out == "3\n"


def test_procedure_without_params(capsys):
    out = run(
        "процедура привет()\n"
        '    печать("Привет")\n'
        "конец\n"
        "процедура пять()\n"
        "    вернуть 5\n"
        "конец\n"
        "выполнить привет()\n"
        'печать("Число: " + выполнить пять())\n',
        capsys,
    )
    assert out == "Привет\nЧисло: 5\n"


def test_call_argument_with_arithmetic(capsys):
    # Внутри вызова арифметика относится к аргументу, а не считается после вызова.
    out = run(
        "процедура плюс_один(a)\n    вернуть a + 1\nконец\n"
        "печать(выполнить плюс_один(1 + 2))\n",
        capsys,
    )
    assert out == "4\n"


def test_procedure_wrong_arg_count():
    src = "процедура о(a)\n    вернуть a\nконец\nпечать(выполнить о(1, 2))\n"
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse(src)))


def test_unknown_procedure():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("выполнить незнакомую(1)")))


def test_infinite_recursion_guard():
    with pytest.raises(LuLangError):
        Interpreter().run(
            build_ast(
                parse(
                    "процедура вечность(x)\n    вернуть выполнить вечность(x)\nконец\n"
                    "печать(выполнить вечность(1))\n"
                )
            )
        )


# --- массивы и объекты ----------------------------------------------------


def test_array_literals(capsys):
    out = run(
        'запомнить фрукты = ["яблоко", "груша", "слива"]\n'
        "печать(фрукты[0])\n"
        'фрукты[1] = "банан"\n'
        "печать(фрукты)\n"
        "печать(длина(фрукты))\n",
        capsys,
    )
    assert out == "яблоко\n[яблоко, банан, слива]\n3\n"


def test_empty_array(capsys):
    out = run("запомнить пусто = []\nпечать(длина(пусто))\n", capsys)
    assert out == "0\n"


def test_array_index_out_of_range():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse('запомнить a = [1]\nпечать(a[5])')))


def test_object_literals(capsys):
    out = run(
        'запомнить кот = {имя: "Лу", возраст: 5}\n'
        "печать(кот.имя)\n"
        "кот.возраст = 6\n"
        'кот.цвет = "рыжий"\n'
        "печать(кот.возраст)\n"
        "печать(кот)\n",
        capsys,
    )
    assert out == "Лу\n6\n{имя: Лу, возраст: 6, цвет: рыжий}\n"


def test_object_unknown_field():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("запомнить к = {a: 1}\nпечать(к.b)")))


def test_length_on_string(capsys):
    out = run('запомнить s = "привет"\nпечать(длина(s))\n', capsys)
    assert out == "6\n"


# --- области видимости ----------------------------------------------------


def test_local_var_in_procedure(capsys):
    # запомнить внутри процедуры создаёт локальную переменную,
    # не затирая глобальную с тем же именем
    out = run(
        "запомнить x = 10\n"
        "процедура тест()\n"
        "    запомнить x = 5\n"
        "    печать(x)\n"
        "конец\n"
        "выполнить тест()\n"
        "печать(x)\n",
        capsys,
    )
    assert out == "5\n10\n"


def test_reassign_global_from_procedure(capsys):
    # переназначение без запомнить внутри процедуры
    # изменяет глобальную переменную
    out = run(
        "запомнить x = 10\n"
        "процедура тест()\n"
        "    x = 20\n"
        "конец\n"
        "печать(x)\n"
        "выполнить тест()\n"
        "печать(x)\n",
        capsys,
    )
    assert out == "10\n20\n"


def test_loop_var_visible_after_loop(capsys):
    # переменная цикла доступна после цикла
    out = run(
        "для i от 1 до 3\n    печать(i)\nконец\n"
        "печать(i)\n",
        capsys,
    )
    assert out == "1\n2\n3\n3\n"


def test_loop_var_inside_procedure(capsys):
    # переменная цикла внутри процедуры не протекает в глобальную область
    out = run(
        "запомнить i = 999\n"
        "процедура тест()\n"
        "    для i от 1 до 3\n        печать(i)\n    конец\n"
        "конец\n"
        "выполнить тест()\n"
        "печать(i)\n",
        capsys,
    )
    assert out == "1\n2\n3\n999\n"


# --- код и символ ----------------------------------------------------------


def test_code_of_char(capsys):
    out = run("печать(код('А'))\n", capsys)
    assert out == "1040\n"


def test_code_in_expression(capsys):
    out = run("печать(код('Б') + 1)\n", capsys)
    assert out == "1042\n"


def test_chr_of_code(capsys):
    out = run("печать(символ(1040))\n", capsys)
    assert out == "А\n"


def test_chr_chain(capsys):
    out = run("печать(символ(код('В') + 1))\n", capsys)
    assert out == "Г\n"


def test_code_on_string_error():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse('печать(код("привет"))')))


def test_chr_invalid_code():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать(символ(-1))")))


def test_chr_bool_error():
    with pytest.raises(LuLangError):
        Interpreter().run(build_ast(parse("печать(символ(истина))")))


# --- строки, массивы, математика -------------------------------------------


def test_string_indexing(capsys):
    out = run('запомнить s = "привет"\nпечать(s[0])\nпечать(s[2])\n', capsys)
    assert out == "п\nи\n"


def test_string_find(capsys):
    out = run('печать(найти("привет", "и"))\n', capsys)
    assert out == "2\n"


def test_string_find_not_found(capsys):
    out = run('печать(найти("привет", "z"))\n', capsys)
    assert out == "-1\n"


def test_substr(capsys):
    out = run('печать(подстрока("привет", 0, 3))\n', capsys)
    assert out == "при\n"


def test_array_add(capsys):
    out = run(
        'запомнить a = [1, 2]\n'
        'добавить(a, 3)\n'
        'печать(a)\n',
        capsys,
    )
    assert out == "[1, 2, 3]\n"


def test_array_remove(capsys):
    out = run(
        'запомнить a = [1, 2, 3]\n'
        'удалить(a, 1)\n'
        'печать(a)\n',
        capsys,
    )
    assert out == "[1, 3]\n"


def test_sqrt(capsys):
    out = run("печать(корень(9))\n", capsys)
    assert out == "3\n"


def test_abs_negative(capsys):
    out = run("печать(модуль(-5))\n", capsys)
    assert out == "5\n"


def test_abs_positive(capsys):
    out = run("печать(модуль(5))\n", capsys)
    assert out == "5\n"


def test_random_range(capsys):
    for _ in range(100):
        out = run("печать(случ(10))\n", capsys)
        val = int(out.strip())
        assert 0 <= val < 10, f"случайное число {val} вне диапазона 0..9"


def test_round_up(capsys):
    out = run("печать(округлить(3.7))\n", capsys)
    assert out == "4\n"


def test_round_down(capsys):
    out = run("печать(округлить(3.2))\n", capsys)
    assert out == "3\n"


def test_upper(capsys):
    out = run('печать(вверх("лу"))\n', capsys)
    assert out == "ЛУ\n"


def test_lower(capsys):
    out = run('печать(вниз("ЛУ"))\n', capsys)
    assert out == "лу\n"


def test_replace(capsys):
    out = run('печать(заменить("котик", "тик", "шка"))\n', capsys)
    assert out == "кошка\n"


def test_split(capsys):
    out = run('печать(разделить("а,б,в", ","))\n', capsys)
    assert out == "[а, б, в]\n"


def test_join(capsys):
    out = run('печать(соединить(["а", "б"], "-"))\n', capsys)
    assert out == "а-б\n"


def test_starts_true(capsys):
    out = run('печать(начинается("привет", "при"))\n', capsys)
    assert out == "истина\n"


def test_starts_false(capsys):
    out = run('печать(начинается("привет", "про"))\n', capsys)
    assert out == "ложь\n"


def test_ends_true(capsys):
    out = run('печать(заканчивается("привет", "вет"))\n', capsys)
    assert out == "истина\n"


def test_reverse(capsys):
    out = run('печать(перевернуть("лу"))\n', capsys)
    assert out == "ул\n"


# --- ввод ----------------------------------------------------------------


def test_input_number(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "10")
    out = run("запомнить n = ввод()\nпечать(n + 1)\n", capsys)
    assert out == "11\n"


def test_input_string(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "Вася")
    out = run("запомнить имя = ввод()\nпечать(имя)\n", capsys)
    assert out == "Вася\n"


# --- файлы ----------------------------------------------------------------


def _file_run(tmp_path, source: str, capsys) -> str:
    """Выполнить исходник, подставляя путь к tmp_path вместо «ПУТЬ»."""
    path = tmp_path / "файл.txt"
    src = source.replace("«ПУТЬ»", f'"{path}"')
    return run(src, capsys)


def test_file_write_and_read_roundtrip(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'файл_записать(«ПУТЬ», "Привет, мир")\n'
        "печать(файл_прочитать(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "Привет, мир\n"


def test_file_write_creates_file(tmp_path, capsys):
    path = tmp_path / "новый.txt"
    out = run(f'файл_записать("{path}", "текст")\n', capsys)
    assert out == ""
    assert path.read_text(encoding="utf-8") == "текст"


def test_file_append_twice(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'файл_записать(«ПУТЬ», "раз")\n'
        'файл_добавить(«ПУТЬ», "два")\n'
        'файл_добавить(«ПУТЬ», "три")\n'
        "печать(файл_прочитать(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "раздватри\n"


def test_file_append_to_missing_creates(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'файл_добавить(«ПУТЬ», "создал")\n'
        "печать(файл_прочитать(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "создал\n"


def test_file_exists(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'печать(файл_существует(«ПУТЬ»))\n'
        'файл_записать(«ПУТЬ», "x")\n'
        "печать(файл_существует(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "ложь\nистина\n"


def test_file_delete(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'файл_записать(«ПУТЬ», "x")\n'
        'файл_удалить(«ПУТЬ»)\n'
        "печать(файл_существует(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "ложь\n"


def test_file_russian_name(tmp_path, capsys):
    path = tmp_path / "заметки.txt"
    out = run(
        f'файл_записать("{path}", "погода")\n'
        f"печать(файл_прочитать(\"{path}\"))\n",
        capsys,
    )
    assert out == "погода\n"


def test_file_read_empty(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        'файл_записать(«ПУТЬ», "")\n'
        'печать("[" + файл_прочитать(«ПУТЬ») + "]")\n',
        capsys,
    )
    assert out == "[]\n"


def test_file_write_number(tmp_path, capsys):
    out = _file_run(
        tmp_path,
        "файл_записать(«ПУТЬ», 42)\n"
        "печать(файл_прочитать(«ПУТЬ»))\n",
        capsys,
    )
    assert out == "42\n"


def test_file_read_missing_raises(tmp_path):
    path = tmp_path / "нет.txt"
    with pytest.raises(LuLangError, match="Не нашёл файл"):
        Interpreter().run(build_ast(parse(f'печать(файл_прочитать("{path}"))')))


def test_file_delete_missing_raises(tmp_path):
    path = tmp_path / "нет.txt"
    with pytest.raises(LuLangError, match="Не нашёл файл"):
        Interpreter().run(build_ast(parse(f'файл_удалить("{path}")')))


def test_file_commands_reserved_as_keywords():
    from lark import LarkError

    for word in (
        "файл_прочитать",
        "файл_записать",
        "файл_добавить",
        "файл_существует",
        "файл_удалить",
    ):
        with pytest.raises(LarkError):
            parse(f"запомнить {word} = 1")


def test_file_read_wrong_type_raises():
    with pytest.raises(LuLangError, match="ожидает строку"):
        Interpreter().run(build_ast(parse("печать(файл_прочитать(5))")))


def test_file_exists_wrong_type_raises():
    with pytest.raises(LuLangError, match="ожидает строку"):
        Interpreter().run(build_ast(parse("печать(файл_существует(истина))")))


# --- переключить / случай ------------------------------------------------


def test_switch_matching_case(capsys):
    out = run(
        "запомнить x = 2\n"
        "переключить x\n"
        "случай 1\n    печать(\"один\")\n"
        "случай 2\n    печать(\"два\")\n"
        "случай 3\n    печать(\"три\")\n"
        "конец\n",
        capsys,
    )
    assert out == "два\n"


def test_switch_first_match_only(capsys):
    # нет проваливания — выполняется только первая подходящая ветка
    out = run(
        "запомнить x = 2\n"
        "переключить x\n"
        "случай 1\n    печать(\"один\")\n"
        "случай 2\n    печать(\"два\")\n"
        "случай 2\n    печать(\"два ещё раз\")\n"
        "конец\n",
        capsys,
    )
    assert out == "два\n"


def test_switch_multiple_values(capsys):
    out = run(
        "запомнить x = 3\n"
        "переключить x\n"
        "случай 1, 2\n    печать(\"мало\")\n"
        "случай 3, 4\n    печать(\"много\")\n"
        "конец\n",
        capsys,
    )
    assert out == "много\n"


def test_switch_else(capsys):
    out = run(
        "запомнить x = 9\n"
        "переключить x\n"
        "случай 1\n    печать(\"один\")\n"
        "иначе\n    печать(\"другое\")\n"
        "конец\n",
        capsys,
    )
    assert out == "другое\n"


def test_switch_no_match_no_else(capsys):
    out = run(
        "запомнить x = 9\n"
        "переключить x\n"
        "случай 1\n    печать(\"один\")\n"
        "конец\n"
        'печать("после")\n',
        capsys,
    )
    assert out == "после\n"


def test_switch_strings(capsys):
    out = run(
        'запомнить цвет = "красный"\n'
        "переключить цвет\n"
        'случай "красный"\n    печать("стоп")\n'
        'случай "зелёный"\n    печать("иди")\n'
        "конец\n",
        capsys,
    )
    assert out == "стоп\n"


def test_switch_expression(capsys):
    out = run(
        "запомнить x = 2\n"
        "переключить x + 1\n"
        "случай 3\n    печать(\"три\")\n"
        "случай 4\n    печать(\"четыре\")\n"
        "конец\n",
        capsys,
    )
    assert out == "три\n"


def test_switch_runs_body_steps(capsys):
    # в ветке выполняются все команды по порядку
    out = run(
        "запомнить x = 1\n"
        "переключить x\n"
        "случай 1\n"
        "    печать(\"а\")\n"
        "    печать(\"б\")\n"
        "конец\n",
        capsys,
    )
    assert out == "а\nб\n"


def test_switch_inside_procedure(capsys):
    out = run(
        "процедура название(день)\n"
        "    переключить день\n"
        "    случай 1\n        вернуть \"понедельник\"\n"
        "    случай 2\n        вернуть \"вторник\"\n"
        "    иначе\n        вернуть \"не знаю\"\n"
        "    конец\n"
        "конец\n"
        "печать(выполнить название(2))\n"
        "печать(выполнить название(9))\n",
        capsys,
    )
    assert out == "вторник\nне знаю\n"


# --- преобразование типов ------------------------------------------------


def test_to_number_from_string(capsys):
    out = run('печать(тип_число("42") + 1)\n', capsys)
    assert out == "43\n"


def test_to_number_fractional_comma(capsys):
    out = run('печать(тип_число("3,5") + 0.5)\n', capsys)
    assert out == "4\n"


def test_to_number_fractional_dot(capsys):
    out = run('печать(тип_число("3.5") + 0.5)\n', capsys)
    assert out == "4\n"


def test_to_number_identity(capsys):
    out = run("печать(тип_число(7))\nпечать(тип_число(2.5))\n", capsys)
    assert out == "7\n2.5\n"


def test_to_number_invalid_raises():
    with pytest.raises(LuLangError, match="в число"):
        Interpreter().run(build_ast(parse('печать(тип_число("абв"))')))


def test_to_number_bool_raises():
    with pytest.raises(LuLangError, match="булево"):
        Interpreter().run(build_ast(parse("печать(тип_число(истина))")))


def test_to_number_wrong_type_raises():
    with pytest.raises(LuLangError, match="ожидает строку или число"):
        Interpreter().run(build_ast(parse("печать(тип_число([1]))")))


def test_to_string_number(capsys):
    out = run('печать("число: " + тип_строка(42))\n', capsys)
    assert out == "число: 42\n"


def test_to_string_bool(capsys):
    out = run('печать(тип_строка(истина) + "!")\n', capsys)
    assert out == "истина!\n"


def test_to_string_nothing(capsys):
    out = run("печать(тип_строка(ничего))\n", capsys)
    assert out == "ничего\n"


def test_to_string_array(capsys):
    out = run('печать(тип_строка([1, 2]))\n', capsys)
    assert out == "[1, 2]\n"


def test_to_string_string_identity(capsys):
    out = run('печать(тип_строка("уже"))\n', capsys)
    assert out == "уже\n"


def test_switch_and_conversion_keywords_reserved():
    from lark import LarkError

    for word in ("переключить", "случай", "тип_число", "тип_строка"):
        with pytest.raises(LarkError):
            parse(f"запомнить {word} = 1")


# --- остаток, перебор, случайное в диапазоне, поиск в массиве -------------


def test_modulo(capsys):
    out = run("печать(остаток(7, 3))\nпечать(остаток(10, 5))\n", capsys)
    assert out == "1\n0\n"


def test_modulo_negative(capsys):
    out = run("печать(остаток(-7, 3))\n", capsys)
    assert out == "2\n"


def test_modulo_float(capsys):
    out = run("печать(остаток(7.5, 2))\n", capsys)
    assert out == "1.5\n"


def test_modulo_by_zero_raises():
    with pytest.raises(LuLangError, match="На ноль"):
        Interpreter().run(build_ast(parse("печать(остаток(1, 0))")))


def test_modulo_wrong_type_raises():
    with pytest.raises(LuLangError, match="ожидает числа"):
        Interpreter().run(build_ast(parse('печать(остаток("а", 2))')))


def test_for_in_array(capsys):
    out = run(
        'запомнить фрукты = ["яблоко", "груша", "слива"]\n'
        "для x из фрукты\n"
        "    печать(x)\n"
        "конец\n",
        capsys,
    )
    assert out == "яблоко\nгруша\nслива\n"


def test_for_in_array_literal(capsys):
    out = run(
        "для x из [1, 2, 3]\n"
        "    печать(x * 2)\n"
        "конец\n",
        capsys,
    )
    assert out == "2\n4\n6\n"


def test_for_in_string(capsys):
    out = run(
        'для б из "лу"\n'
        "    печать(б)\n"
        "конец\n",
        capsys,
    )
    assert out == "л\nу\n"


def test_for_in_var_after_loop(capsys):
    # переменная цикла доступна после цикла и хранит последний элемент
    out = run(
        "для x из [1, 2, 3]\n"
        "    печать(x)\n"
        "конец\n"
        "печать(x)\n",
        capsys,
    )
    assert out == "1\n2\n3\n3\n"


def test_for_in_empty_array(capsys):
    out = run(
        "для x из []\n"
        "    печать(x)\n"
        "конец\n"
        'печать("после")\n',
        capsys,
    )
    assert out == "после\n"


def test_for_in_break(capsys):
    out = run(
        "для x из [1, 2, 3, 4]\n"
        "    если x = 3 то\n        прервать\n    конец\n"
        "    печать(x)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n2\n"


def test_for_in_continue(capsys):
    out = run(
        "для x из [1, 2, 3]\n"
        "    если x = 2 то\n        продолжить\n    конец\n"
        "    печать(x)\n"
        "конец\n",
        capsys,
    )
    assert out == "1\n3\n"


def test_for_in_wrong_type_raises():
    with pytest.raises(LuLangError, match="массивами и строками"):
        Interpreter().run(build_ast(parse("для x из 5\n    печать(x)\nконец")))


def test_for_in_sum(capsys):
    out = run(
        "запомнить сумма = 0\n"
        "для x из [1, 2, 3, 4]\n"
        "    сумма = сумма + x\n"
        "конец\n"
        "печать(сумма)\n",
        capsys,
    )
    assert out == "10\n"


def test_random_range_inclusive(capsys):
    for _ in range(100):
        out = run("печать(случ(1, 6))\n", capsys)
        val = int(out.strip())
        assert 1 <= val <= 6, f"случайное число {val} вне диапазона 1..6"


def test_random_range_single_value(capsys):
    out = run("печать(случ(7, 7))\n", capsys)
    assert out == "7\n"


def test_random_range_reversed_raises():
    with pytest.raises(LuLangError, match="больше конца"):
        Interpreter().run(build_ast(parse("печать(случ(5, 1))")))


def test_random_old_single_arg_still_works(capsys):
    for _ in range(50):
        out = run("печать(случ(10))\n", capsys)
        val = int(out.strip())
        assert 0 <= val < 10


def test_find_in_array(capsys):
    out = run(
        'запомнить a = ["яблоко", "груша", "слива"]\n'
        'печать(найти(a, "груша"))\n'
        'печать(найти(a, "персик"))\n',
        capsys,
    )
    assert out == "1\n-1\n"


def test_find_in_number_array(capsys):
    out = run("печать(найти([10, 20, 30], 30))\nпечать(найти([10, 20], 15))\n", capsys)
    assert out == "2\n-1\n"


def test_find_string_still_works(capsys):
    out = run('печать(найти("привет", "и"))\n', capsys)
    assert out == "2\n"


def test_ostatok_keyword_reserved():
    from lark import LarkError

    with pytest.raises(LarkError):
        parse("запомнить остаток = 1")


# --- черепашка (графика) -------------------------------------------------


_ЧЕРЕПАШКА_ПУТЬ = (
    Path(__file__).resolve().parent.parent / "lulang" / "библиотеки" / "черепашка.py"
)


def test_turtle_module_has_commands():
    """Модуль объявляет все команды черепашки (не требует дисплея)."""
    import re

    source = _ЧЕРЕПАШКА_ПУТЬ.read_text(encoding="utf-8")
    for name in (
        "вперёд",
        "назад",
        "вправо",
        "влево",
        "поднять_перо",
        "опустить_перо",
        "цвет",
        "круг",
        "точка",
        "скорость",
        "готово",
    ):
        assert re.search(rf"^def {name}\(", source, re.M), f"в модуле нет команды {name}"


def test_turtle_module_loads_without_window():
    """Подключение модуля не открывает окно (нужен графический экран)."""
    pytest.importorskip("turtle")
    interp = Interpreter()
    interp.run(build_ast(parse("подключить черепашка")))
    assert "черепашка" in interp.modules


# --- модули ---------------------------------------------------------------


def run_in(tmp_path, source: str, capsys) -> str:
    """Выполнить исходник, ища модули в tmp_path."""
    program = build_ast(parse(source))
    Interpreter(module_paths=[tmp_path]).run(program)
    return capsys.readouterr().out


def test_import_lu_module(tmp_path, capsys):
    (tmp_path / "математика.lu").write_text(
        "процедура квадрат(число)\n"
        "    вернуть число * число\n"
        "конец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить математика\n"
        "запомнить x = выполнить математика.квадрат(5)\n"
        "печать(x)\n",
        capsys,
    )
    assert out == "25\n"


def test_import_lu_module_calls_sibling(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура двойной(x)\n    вернуть x + x\nконец\n"
        "процедура учетверённый(x)\n    вернуть выполнить двойной(x + x)\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить м\nпечать(выполнить м.учетверённый(3))\n",
        capsys,
    )
    assert out == "12\n"


def test_import_with_alias(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура привет()\n    вернуть \"Лу\"\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить м как мат\nпечать(выполнить мат.привет())\n",
        capsys,
    )
    assert out == "Лу\n"
    # настоящее имя тоже доступно — импорт не выполняется второй раз
    assert "Я ещё не знаю" not in out


def test_python_plugin_module(tmp_path, capsys):
    (tmp_path / "маг.py").write_text(
        "def удвой(x):\n    return x * 2\n\ndef _секрет(x):\n    return 0\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить маг\nпечать(выполнить маг.удвой(21))\n",
        capsys,
    )
    assert out == "42\n"
    with pytest.raises(LuLangError):
        run_in(tmp_path, "подключить маг\nпечать(выполнить маг._секрет(1))\n", capsys)


def test_python_plugin_with_all(tmp_path, capsys):
    (tmp_path / "м.py").write_text(
        "def а(x):\n    return 1\n"
        "def б(x):\n    return 2\n"
        "__все__ = [\"б\"]\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить м\nпечать(выполнить м.б(0))\n",
        capsys,
    )
    assert out == "2\n"
    with pytest.raises(LuLangError):
        run_in(tmp_path, "подключить м\nпечать(выполнить м.а(0))\n", capsys)


def test_module_imported_once(tmp_path, capsys):
    (tmp_path / "счёт.lu").write_text(
        'печать("тело!")\nпроцедура значение()\n    вернуть 7\nконец\n',
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить счёт\nподключить счёт\nпечать(выполнить счёт.значение())\n",
        capsys,
    )
    assert out == "тело!\n7\n"


def test_module_globals_isolated(tmp_path, capsys):
    (tmp_path / "изол.lu").write_text(
        "запомнить секрет = 10\n"
        "процедура получить()\n    вернуть секрет\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "запомнить секрет = 5\n"
        "подключить изол\n"
        "печать(выполнить изол.получить())\n"
        "печать(секрет)\n",
        capsys,
    )
    assert out == "10\n5\n"


def test_builtin_lib_module(tmp_path, capsys):
    out = run_in(
        tmp_path,
        "подключить математика\nпечать(выполнить математика.квадрат(4))\n",
        capsys,
    )
    assert out == "16\n"


def test_module_not_found():
    with pytest.raises(LuLangError, match="Не нашёл модуль"):
        Interpreter().run(build_ast(parse("подключить несуществующий")))


def test_module_not_imported_call_raises():
    with pytest.raises(LuLangError, match="Не подключён модуль"):
        Interpreter().run(build_ast(parse("печать(выполнить математика.квадрат(5))")))


# --- импорт имён: из ... взять ... ----------------------------------------


def test_from_import_name(tmp_path, capsys):
    (tmp_path / "геометрия.lu").write_text(
        "процедура периметр_квадрата(сторона)\n    вернуть 4 * сторона\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из геометрия взять периметр_квадрата\n"
        "печать(выполнить периметр_квадрата(5))\n",
        capsys,
    )
    assert out == "20\n"


def test_from_import_uses_module_globals(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "запомнить пи = 3\n"
        "процедура тройной(x)\n    вернуть пи * x\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из м взять тройной\n"
        "запомнить пи = 999\n"
        "печать(выполнить тройной(2))\n",
        capsys,
    )
    assert out == "6\n"  # берётся глобал модуля, а не программы


def test_from_import_calls_sibling(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура двойной(x)\n    вернуть x + x\nконец\n"
        "процедура учетверённый(x)\n    вернуть (выполнить двойной(x + x))\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из м взять учетверённый\nпечать(выполнить учетверённый(3))\n",
        capsys,
    )
    assert out == "12\n"


def test_from_import_with_alias(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура привет()\n    вернуть \"Лу\"\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из м взять привет как п\nпечать(выполнить п())\n",
        capsys,
    )
    assert out == "Лу\n"
    with pytest.raises(LuLangError, match="Не знаю такую процедуру"):
        run_in(tmp_path, "из м взять привет как п\nпечать(выполнить привет())\n", capsys)


def test_from_import_several_names(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура а(x)\n    вернуть x + 1\nконец\n"
        "процедура б(x)\n    вернуть x + 2\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из м взять а, б как в\n"
        "печать(выполнить а(1))\n"
        "печать(выполнить в(1))\n",
        capsys,
    )
    assert out == "2\n3\n"


def test_from_import_all(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура а(x)\n    вернуть x + 1\nконец\n"
        "процедура б(x)\n    вернуть x + 2\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из м взять всё\nпечать(выполнить а(1))\nпечать(выполнить б(1))\n",
        capsys,
    )
    assert out == "2\n3\n"


def test_from_import_python_plugin(tmp_path, capsys):
    (tmp_path / "маг.py").write_text(
        "def удвой(x):\n    return x * 2\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "из маг взять удвой\nпечать(выполнить удвой(21))\n",
        capsys,
    )
    assert out == "42\n"


def test_from_import_unknown_name(tmp_path):
    (tmp_path / "м.lu").write_text(
        "процедура а(x)\n    вернуть x\nконец\n",
        encoding="utf-8",
    )
    with pytest.raises(LuLangError, match="нет процедуры"):
        Interpreter(module_paths=[tmp_path]).run(build_ast(parse("из м взять несуществующая\n")))


def test_from_import_unknown_module(tmp_path):
    with pytest.raises(LuLangError, match="Не нашёл модуль"):
        Interpreter(module_paths=[tmp_path]).run(build_ast(parse("из несуществующий взять а\n")))


def test_from_import_not_imported_name():
    with pytest.raises(LuLangError, match="Не знаю такую процедуру"):
        Interpreter().run(build_ast(parse("печать(выполнить площадь_круга(1))")))


def test_from_import_local_proc_wins(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        "процедура тест()\n    вернуть \"из модуля\"\nконец\n",
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "процедура тест()\n    вернуть \"своя\"\nконец\n"
        "из м взять тест\n"
        "печать(выполнить тест())\n",
        capsys,
    )
    assert out == "своя\n"


def test_from_import_module_not_reexecuted(tmp_path, capsys):
    (tmp_path / "м.lu").write_text(
        'печать("тело!")\nпроцедура а(x)\n    вернуть x\nконец\n',
        encoding="utf-8",
    )
    out = run_in(
        tmp_path,
        "подключить м\nиз м взять а\nпечать(выполнить а(1))\n",
        capsys,
    )
    assert out == "тело!\n1\n"


# --- интерактивный режим (REPL) ------------------------------------------


def test_repl_expression_result(capsys):
    from lulang.repl import _try_run

    interp = Interpreter()
    status, err = _try_run("2 + 2\n", interp)
    assert status == "ok"
    assert err is None
    assert capsys.readouterr().out == "4\n"


def test_repl_statement_no_output(capsys):
    from lulang.repl import _try_run

    interp = Interpreter()
    status, err = _try_run("запомнить x = 5\n", interp)
    assert status == "ok"
    assert capsys.readouterr().out == ""


def test_repl_incomplete_block():
    from lulang.repl import _try_run

    interp = Interpreter()
    status, err = _try_run("процедура квадрат(число)\n    вернуть число * число\n", interp)
    assert status == "incomplete"


def test_repl_persistent_state(capsys):
    from lulang.repl import _try_run

    interp = Interpreter()
    _try_run("запомнить x = 5\n", interp)
    status, err = _try_run("x * 2\n", interp)
    assert status == "ok"
    assert capsys.readouterr().out == "10\n"


def test_repl_runtime_error_keeps_session(capsys):
    from lulang.repl import _try_run

    interp = Interpreter()
    status, err = _try_run("печать(1 / 0)\n", interp)
    assert status == "error"
    assert "делить" in str(err)
    status, err = _try_run('печать("ок")\n', interp)
    assert status == "ok"


def test_repl_exit_via_command(monkeypatch, capsys):
    from lulang.repl import repl

    lines = iter(["печать(1 + 1)", "выход()"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(lines))
    repl()
    assert "2" in capsys.readouterr().out


def test_repl_exit_via_eof(monkeypatch, capsys):
    from lulang.repl import repl

    def no_input(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_input)
    repl()  # не должно бросить исключение
    assert "интерактивный режим" in capsys.readouterr().out


def test_repl_help(monkeypatch, capsys):
    from lulang.repl import repl

    lines = iter(["помощь()", "выход()"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(lines))
    repl()
    assert "Специальные команды" in capsys.readouterr().out


def test_repl_multiline_procedure(monkeypatch, capsys):
    from lulang.repl import repl

    lines = iter(
        [
            "процедура квадрат(число)",
            "    вернуть число * число",
            "конец",
            "выполнить квадрат(4)",
            "выход()",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(lines))
    repl()
    # квадрат(4) — инструкция без печати, но процедура должна зарегистрироваться
    out = capsys.readouterr().out
    assert "интерактивный режим" in out