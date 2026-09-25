#!/usr/bin/env bash
#
# build.sh — собрать standalone-бинарник lu-lang (PyInstaller).
#
# Результат: dist/lu — один исполняемый файл, который не требует Python
# на целевой машине. По умолчанию бинарник копируется в ~/.local/bin/lu
# (или в bin указанного префикса).
#
# Встроенные библиотеки (lulang/библиотеки/*.lu и *.py) попадают в
# бинарник автоматически — команда `--collect-all lulang` кладёт их
# в bundle, а интерпретатор умеет искать их в собранном виде.
#
# Использование:
#   ./build.sh                       собрать и установить в ~/.local/bin
#   ./build.sh --no-install          только собрать (результат: dist/lu)
#   ./build.sh --prefix DIR          установить в DIR/bin
#   ./build.sh --clean               пересоздать окружение сборки
#   ./build.sh --python PYTHON       какой интерпретатор использовать
#   ./build.sh --help                показать это сообщение
#
# Подробная документация: см. INSTALL.md.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX="${PREFIX:-$HOME/.local}"
BUILD_VENV="${LU_BUILD_VENV:-$ROOT_DIR/.build-venv}"
PYTHON_BIN="${PYTHON:-python3}"
INSTALL=1
CLEAN=0

usage() {
    sed -n '2,21p' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --python) PYTHON_BIN="$2"; shift 2 ;;
        --no-install) INSTALL=0; shift ;;
        --clean) CLEAN=1; shift ;;
        --help) usage ;;
        *) echo "Неизвестный аргумент: $1" >&2; usage ;;
    esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Не найден интерпретатор Python: $PYTHON_BIN" >&2
    exit 1
fi

if [[ "$CLEAN" -eq 1 ]]; then
    rm -rf "$BUILD_VENV" "$ROOT_DIR/build" "$ROOT_DIR/dist"
fi

if [[ ! -x "$BUILD_VENV/bin/python" ]]; then
    echo "Создаю окружение сборки в $BUILD_VENV ..."
    "$PYTHON_BIN" -m venv "$BUILD_VENV"
else
    echo "Использую окружение сборки в $BUILD_VENV ..."
fi

echo "Устанавливаю средства сборки ..."
"$BUILD_VENV/bin/pip" install --upgrade pip >/dev/null
"$BUILD_VENV/bin/pip" install pyinstaller
"$BUILD_VENV/bin/pip" install "$ROOT_DIR"

echo
echo "Собираю бинарник (PyInstaller $( "$BUILD_VENV/bin/pyinstaller" --version )) ..."
mkdir -p "$ROOT_DIR/build"
# Точка входа для PyInstaller: __main__.py использует относительный импорт,
# который работает только в составе пакета, поэтому берём отдельный файл.
_ENTRY="$ROOT_DIR/build/_entry_lu.py"
cat > "$_ENTRY" <<'PY'
import sys

from lulang.cli import main

sys.exit(main())
PY
"$BUILD_VENV/bin/pyinstaller" \
    --onefile \
    --name lu \
    --collect-all lulang \
    --distpath "$ROOT_DIR/dist" \
    --workpath "$ROOT_DIR/build" \
    --specpath "$ROOT_DIR/build" \
    --noconfirm \
    "$_ENTRY"

echo
echo "Проверяю бинарник ..."
"$ROOT_DIR/dist/lu" --version
"$ROOT_DIR/dist/lu" "$ROOT_DIR/examples/hello.lu" >/dev/null \
    && echo "  hello.lu — ок"
"$ROOT_DIR/dist/lu" "$ROOT_DIR/examples/модули.lu" >/dev/null \
    && echo "  модули.lu — ок"
_check_lu="$ROOT_DIR/build/_check_библиотеки.lu"
printf 'подключить математика\nпечать(выполнить математика.квадрат(4))\n' > "$_check_lu"
if [[ "$("$ROOT_DIR/dist/lu" "$_check_lu")" == "16" ]]; then
    echo "  встроенная библиотека (математика) — ок"
else
    echo "  ОШИБКА: встроенная библиотека не найдена в бинарнике" >&2
    exit 1
fi
rm -f "$_check_lu"

if [[ "$INSTALL" -eq 1 ]]; then
    mkdir -p "$PREFIX/bin"
    rm -f "$PREFIX/bin/lu"
    cp "$ROOT_DIR/dist/lu" "$PREFIX/bin/lu"
    echo
    echo "Бинарник установлен: $PREFIX/bin/lu"
    "$PREFIX/bin/lu" --version
else
    echo
    echo "Готово. Бинарник: $ROOT_DIR/dist/lu"
fi