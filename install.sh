#!/usr/bin/env bash
#
# install.sh — установка lu-lang в систему.
#
# Скрипт создаёт виртуальное окружение в каталоге проекта, устанавливает
# в него пакет и помещает команду `lu` в каталог bin указанного префикса
# (по умолчанию — ~/.local/bin), откуда команда доступна из любого места.
#
# Использование:
#   ./install.sh                       установить в ~/.local/bin
#   ./install.sh --prefix DIR          установить команду в DIR/bin
#   ./install.sh --venv DIR            использовать виртуальное окружение DIR
#   ./install.sh --python PYTHON       какой интерпретатор использовать
#   ./install.sh --uninstall           удалить команду lu
#   ./install.sh --help                показать это сообщение

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX="${PREFIX:-$HOME/.local}"
VENV_DIR="${LU_VENV:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON:-python3}"
UNINSTALL=0

usage() {
    sed -n '2,20p' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --venv) VENV_DIR="$2"; shift 2 ;;
        --python) PYTHON_BIN="$2"; shift 2 ;;
        --uninstall) UNINSTALL=1; shift ;;
        --help) usage ;;
        *) echo "Неизвестный аргумент: $1" >&2; usage ;;
    esac
done

BIN_DIR="$PREFIX/bin"
COMMAND="$BIN_DIR/lu"

if [[ "$UNINSTALL" -eq 1 ]]; then
    if [[ -e "$COMMAND" || -L "$COMMAND" ]]; then
        rm -f "$COMMAND"
        echo "Команда $COMMAND удалена."
    else
        echo "Команда $COMMAND не установлена." >&2
    fi
    exit 0
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Не найден интерпретатор Python: $PYTHON_BIN" >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Требуется Python 3.10 или новее, а найдена версия:" >&2
    "$PYTHON_BIN" --version >&2
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Создаю виртуальное окружение в $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "Использую существующее виртуальное окружение в $VENV_DIR ..."
fi

echo "Устанавливаю пакет lu-lang ..."
"$VENV_DIR/bin/pip" install -e "$ROOT_DIR"

mkdir -p "$BIN_DIR"
rm -f "$COMMAND"
ln -s "$VENV_DIR/bin/lu" "$COMMAND"

echo "Команда установлена: $COMMAND"
"$VENV_DIR/bin/lu" --version

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo "Внимание: каталог $BIN_DIR отсутствует в PATH."
    echo "Добавьте его, например, в ~/.bashrc:"
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
fi