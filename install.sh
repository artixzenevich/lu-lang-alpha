#!/usr/bin/env bash
#
# install.sh — установка lu-lang в систему.
#
# Скрипт создаёт виртуальное окружение ВНЕ проекта (по умолчанию
# ~/.local/share/lu-lang/venv), устанавливает в него пакет и помещает
# команду `lu` в ~/.local/bin (или в bin указанного префикса). Установка
# standalone — пакет копируется, от каталога проекта она не зависит.
# Если ~/.local/bin отсутствует в PATH, скрипт сам добавит его в
# ~/.bashrc / ~/.profile / ~/.zshrc.
#
# Использование:
#   ./install.sh                       установить (standalone, в ~/.local/bin)
#   ./install.sh --update              переустановить пакет из этого каталога
#   ./install.sh --dev                 для разработки: editable-установка
#                                      в виртуальное окружение проекта (.venv)
#   ./install.sh --prefix DIR          установить команду в DIR/bin
#   ./install.sh --venv DIR            использовать виртуальное окружение DIR
#   ./install.sh --python PYTHON       какой интерпретатор использовать
#   ./install.sh --uninstall           удалить команду lu, venv и строку PATH
#   ./install.sh --help                показать это сообщение
#
# Подробная документация: см. INSTALL.md.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX="${PREFIX:-$HOME/.local}"
SHARE_DIR="${LU_SHARE:-$HOME/.local/share/lu-lang}"
VENV_DIR="${LU_VENV:-$SHARE_DIR/venv}"
PYTHON_BIN="${PYTHON:-python3}"
DEV=0
UPDATE=0
UNINSTALL=0

usage() {
    sed -n '2,24p' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --venv) VENV_DIR="$2"; shift 2 ;;
        --python) PYTHON_BIN="$2"; shift 2 ;;
        --dev) DEV=1; shift ;;
        --update) UPDATE=1; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        --help) usage ;;
        *) echo "Неизвестный аргумент: $1" >&2; usage ;;
    esac
done

if [[ "$DEV" -eq 1 ]]; then
    VENV_DIR="$ROOT_DIR/.venv"
fi

BIN_DIR="$PREFIX/bin"
COMMAND="$BIN_DIR/lu"

# --- работа с PATH ---------------------------------------------------------

_rc_files=()
for _rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
    [[ -f "$_rc" ]] && _rc_files+=("$_rc")
done

_add_bin_to_path() {
    local added=0
    local line="export PATH=\"$BIN_DIR:\$PATH\""
    for rc in "${_rc_files[@]}"; do
        if ! grep -qF -- "# >>> lu-lang >>>" "$rc"; then
            printf '\n# >>> lu-lang >>>\n%s\n# <<< lu-lang <<<\n' "$line" >> "$rc"
            echo "Добавил $BIN_DIR в PATH (файл $rc)."
            added=1
        fi
    done
    return $((added ? 0 : 1))
}

_remove_bin_from_path() {
    for rc in "${_rc_files[@]}"; do
        [[ -f "$rc" ]] || continue
        if grep -qF -- "# >>> lu-lang >>>" "$rc"; then
            sed -i '/# >>> lu-lang >>>/,/# <<< lu-lang <<</d' "$rc"
            echo "Убрал строку lu-lang из PATH (файл $rc)."
        fi
    done
}

# --- удаление --------------------------------------------------------------

if [[ "$UNINSTALL" -eq 1 ]]; then
    if [[ -e "$COMMAND" || -L "$COMMAND" ]]; then
        rm -f "$COMMAND"
        echo "Команда $COMMAND удалена."
    else
        echo "Команда $COMMAND не установлена." >&2
    fi
    if [[ -d "$VENV_DIR" ]]; then
        rm -rf "$VENV_DIR"
        echo "Вируальное окружение $VENV_DIR удалено."
    fi
    _remove_bin_from_path
    exit 0
fi

# --- установка -------------------------------------------------------------

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
    echo "Создаю вируальное окружение в $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "Использую вируальное окружение в $VENV_DIR ..."
fi

if ! "$VENV_DIR/bin/python" -c 'import turtle, tkinter' >/dev/null 2>&1; then
    echo
    echo "ВНИМАНИЕ: в этом Python нет tkinter/turtle — встроенная библиотека"
    echo "«черепашка» работать не будет. Нужен Python с Tk, например на NixOS:"
    echo "  nix-shell -p 'python3.withPackages (ps: [ ps.tkinter ])' --run './install.sh'"
    echo "  (Debian: sudo apt install python3-tk)"
    echo
fi

if [[ "$DEV" -eq 1 ]]; then
    echo "Устанавливаю пакет lu-lang в режиме разработки (editable) ..."
    "$VENV_DIR/bin/pip" install -e "$ROOT_DIR"
else
    if [[ "$UPDATE" -eq 1 ]]; then
        echo "Обновляю пакет lu-lang ..."
        "$VENV_DIR/bin/pip" install --force-reinstall "$ROOT_DIR"
    else
        echo "Устанавливаю пакет lu-lang ..."
        "$VENV_DIR/bin/pip" install "$ROOT_DIR"
    fi
fi

mkdir -p "$BIN_DIR"
ln -sfn "$VENV_DIR/bin/lu" "$COMMAND"

echo
echo "Команда установлена: $COMMAND"
"$VENV_DIR/bin/lu" --version

if _add_bin_to_path; then
    echo
    echo "Каталог $BIN_DIR добавлен в файл(ы) профиля. Чтобы изменения"
    echo "вступили в силу, откройте новый терминал или выполните:"
    echo "    source ~/.bashrc"
elif [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo "Каталог $BIN_DIR отсутствует в PATH, и я не нашёл ни одного файла"
    echo "профиля (~/.bashrc, ~/.profile, ~/.zshrc). Добавьте строку вручную"
    echo "в свой файл профиля (или настройте PATH в системе):"
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
fi