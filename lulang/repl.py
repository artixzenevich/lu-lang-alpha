"""Интерактивный режим lu-lang (REPL).

Запуск:  lu   (без аргументов)

Поведение как у Python:
    - выражение сразу печатает результат (2 + 2 -> 4);
    - незавершённый блок (процедура ... конец) продолжается с приглашением ...;
    - Ctrl+D или выход() завершают сессию, Ctrl+C очищает строку;
    - стрелки вверх/вниз листают историю (readline).
"""

try:
    import readline  # noqa: F401  # история и редактирование строки
except ImportError:  # pragma: no cover
    pass

from lark import UnexpectedEOF, UnexpectedInput

from . import __version__
from .ast_builder import build_ast
from .grammar import parse
from .interpreter import Interpreter, LuLangError

_PROMPT = "lu> "
_CONTINUATION = "... "

_HELP = f"""\
lu-lang {__version__} — интерактивный режим

Пиши команды и выражения как в обычной программе:

    печать("Привет, мир")
    запомнить x = 5
    x * 2                  # результат выражения печатается сразу
    процедура квадрат(число)
        вернуть число * число
    конец
    выполнить квадрат(5)
    подключить математика

Специальные команды:
    помощь()   — показать эту справку
    выход()    — выйти из интерактивного режима

Выход также: Ctrl+D. Стрелки вверх/вниз — история команд.
"""


def _try_run(src, interp):
    """Выполнить фрагмент интерактивной сессии.

    Возвращает ("ok", None), ("incomplete", None) или ("error", исключение).
    Если текст не является командой, но является выражением — выполняет его
    как печать(выражение), как делает REPL Python.
    """
    try:
        tree = parse(src)
    except UnexpectedEOF:
        try:
            tree = parse(f"печать({src.strip()})")
        except Exception:
            return "incomplete", None
    except Exception as exc:
        try:
            tree = parse(f"печать({src.strip()})")
        except Exception:
            return "error", exc
    try:
        program = build_ast(tree)
        interp.run(program)
    except LuLangError as exc:
        return "error", exc
    return "ok", None


def repl() -> None:
    """Запустить интерактивный цикл (REPL)."""
    interp = Interpreter()
    print(f"lu-lang {__version__} — интерактивный режим. Выход: Ctrl+D или выход().")
    print("Справка: помощь()")
    buffer = ""
    while True:
        prompt = _CONTINUATION if buffer else _PROMPT
        try:
            line = input(prompt)
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            print()
            buffer = ""
            continue

        stripped = line.strip()
        if not buffer and stripped == "выход()":
            return
        if not buffer and stripped == "помощь()":
            print(_HELP)
            continue

        buffer += line + "\n"
        status, err = _try_run(buffer, interp)
        if status == "incomplete":
            continue
        buffer = ""
        if status == "error":
            if isinstance(err, LuLangError):
                print(f"Ой! {err}")
            else:
                print(f"Не понял команду. Ошибка: {err}")