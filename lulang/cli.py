"""Командная строка lu-lang.

Запуск:
    lu program.lu            — выполнить программу
    lu program.lu --show-ast — заодно показать дерево разбора
    lu                       — интерактивный режим (REPL)
"""

import argparse
import sys
from pathlib import Path

from lark import LarkError

from . import __version__
from .ast_builder import build_ast
from .grammar import parse
from .interpreter import Interpreter, LuLangError


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lu",
        description="lu-lang — детский язык программирования на русском.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="ФАЙЛ",
        help="путь к программе на lu-lang (расширение .lu); без файла — интерактивный режим",
    )
    parser.add_argument(
        "--show-ast",
        action="store_true",
        help="показать дерево разбора и выйти",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"lu-lang {__version__}",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.file is None:
        from .repl import repl

        repl()
        return 0

    path = Path(args.file)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Не могу прочитать файл {path}: {exc}", file=sys.stderr)
        return 1

    try:
        tree = parse(source)
    except LarkError as exc:
        print("Не понял команду. Ошибка:", exc, file=sys.stderr)
        return 1

    if args.show_ast:
        print(tree.pretty())
        return 0

    try:
        program = build_ast(tree)
    except Exception as exc:  # ошибки конструкции AST
        print("Не понял команду. Ошибка:", exc, file=sys.stderr)
        return 1

    try:
        Interpreter(module_paths=[path.parent]).run(program)
    except LuLangError as exc:
        print(f"Ой! {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())