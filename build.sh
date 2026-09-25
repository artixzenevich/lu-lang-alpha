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
# Вся стандартная библиотека Python вшивается целиком: PyInstaller не
# видит динамические импорты из библиотек-плагинов (importlib), поэтому
# без этого в бинарнике оказалась бы лишь часть stdlib.
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

# На NixOS Python с пакетами (python3.withPackages) кладёт tkinter в
# site-packages, которую venv по умолчанию прячет. Если в окружении сборки
# нет tkinter, а в базовом интерпретаторе он есть — пересоздаём окружение
# с --system-site-packages, чтобы библиотеки из базового Python были видны.
if ! "$BUILD_VENV/bin/python" -c 'import turtle, tkinter' >/dev/null 2>&1 \
    && "$PYTHON_BIN" -c 'import turtle, tkinter' >/dev/null 2>&1; then
    echo "В базовом Python есть tkinter — пересоздаю окружение сборки"
    echo "с --system-site-packages ..."
    rm -rf "$BUILD_VENV"
    "$PYTHON_BIN" -m venv --system-site-packages "$BUILD_VENV"
fi

echo "Устанавливаю средства сборки ..."
"$BUILD_VENV/bin/pip" install --upgrade pip >/dev/null
"$BUILD_VENV/bin/pip" install pyinstaller
"$BUILD_VENV/bin/pip" install "$ROOT_DIR"

# Проверка tkinter/turtle: PyInstaller не видит их через динамические
# импорты, а данные Tk на некоторых системах (NixOS) лежат не рядом с Tcl.
_TK_OK=0
echo
echo "Проверяю окружение сборки ..."
if "$BUILD_VENV/bin/python" -c 'import turtle, tkinter' >/dev/null 2>&1; then
    _TK_OK=1
    echo "  tkinter/turtle есть — «черепашка» попадёт в бинарник"
    # PyInstaller ищет данные Tk рядом с данными Tcl (../tkX.Y), а на NixOS
    # они лежат в отдельном каталоге nix-store. Подскажем ему пути явно.
    while IFS='=' read -r _k _v; do
        [[ -n "$_k" ]] && export "$_k=$_v"
    done < <("$BUILD_VENV/bin/python" - <<'PY'
import glob
import os
import tkinter
import _tkinter

tcl = tkinter.Tcl()
tcl_dir = tcl.eval("info library")
tk_ver = f"{_tkinter.TK_VERSION}"
print(f"TCL_LIBRARY={tcl_dir}")
tk_cand = os.path.join(os.path.dirname(tcl_dir), "tk" + tk_ver)
if not os.path.isdir(tk_cand):
    for p in sorted(glob.glob(f"/nix/store/*tk-*/lib/tk{tk_ver}")):
        if os.path.isdir(p):
            tk_cand = p
            break
print(f"TK_LIBRARY={tk_cand}")
PY
)
else
    cat >&2 <<'EOF'
  ВНИМАНИЕ: в интерпретаторе сборки нет tkinter/turtle, поэтому
  встроенная библиотека «черепашка» в бинарнике работать не будет.
  Соберите окружение Python с tkinter и повторите:

    NixOS:      nix-shell -p 'python3.withPackages (ps: [ ps.tkinter ])' \
                          --run './build.sh --clean'
    Debian:     sudo apt install python3-tk
    Fedora:     sudo dnf install python3-tkinter
    Arch:       sudo pacman -S tk
EOF
fi

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
# Стандартная библиотека Python целиком: встроенные библиотеки-плагины
# (lulang/библиотеки/*.py) и пользовательские модули грузятся через
# importlib, поэтому PyInstaller не видит их импорты. Вшиваем все модули
# stdlib, чтобы в бинарнике была доступна любая из них (черепашка,
# sqlite3, json, http, xml и т.д.).
echo
echo "Собираю полный список стандартных библиотек ..."
mapfile -t _STDLIB_HIDDEN < <(
    "$BUILD_VENV/bin/python" - <<'PY'
import importlib.util
import sys

SKIP = {"test", "antigravity", "this", "ensurepip", "lib2to3", "idlelib", "venv"}
for name in sorted(sys.stdlib_module_names):
    if name in SKIP or name.startswith("test"):
        continue
    # Пропускаем модули других платформ (например, Windows-only
    # _overlapped, winsound): их нет в этом Python, и PyInstaller
    # завалит лог ошибками «Hidden import not found».
    if importlib.util.find_spec(name) is None:
        continue
    print(name)
PY
)
echo "  ${#_STDLIB_HIDDEN[@]} модулей стандартной библиотеки"

_PYI_OPTS=(
    --onefile
    --name lu
    --collect-all lulang
    "${_STDLIB_HIDDEN[@]/#/--hidden-import=}"
)
"$BUILD_VENV/bin/pyinstaller" \
    "${_PYI_OPTS[@]}" \
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

if [[ "$_TK_OK" -eq 1 ]]; then
    _check_turtle="$ROOT_DIR/build/_check_черепашка.lu"
    printf 'подключить черепашка\nпечать("ок")\n' > "$_check_turtle"
    if [[ "$("$ROOT_DIR/dist/lu" "$_check_turtle")" == "ок" ]]; then
        echo "  встроенная библиотека (черепашка) — ок"
    else
        echo "  ОШИБКА: черепашка не загружается в бинарнике" >&2
        exit 1
    fi
    rm -f "$_check_turtle"
fi

_check_stdlib_py="$ROOT_DIR/build/check_stdlib.py"
_check_stdlib_lu="$ROOT_DIR/build/_check_stdlib.lu"
_STDLIB_CHECK_MODULES=(
    "math" "time" "os" "sys" "json" "sqlite3" "random" "re"
    "collections" "itertools" "functools" "datetime" "csv" "pathlib"
    "tempfile" "shutil" "hashlib" "base64" "binascii" "struct"
    "socket" "ssl" "zlib" "gzip" "bz2" "lzma" "subprocess" "threading"
    "urllib" "http" "xml" "email" "logging" "argparse" "configparser"
    "difflib" "textwrap" "traceback" "inspect" "pkgutil" "importlib"
    "string" "unicodedata" "heapq" "bisect" "decimal" "fractions"
    "statistics" "cmath" "turtle" "tkinter" "ctypes" "asyncio"
    "multiprocessing" "pickle"
)
# Если в окружении сборки нет Tk, turtle/tkinter в бинарник не попадают —
# исключаем их из самопроверки, чтобы сборка не падала (см. INSTALL.md).
if [[ "$_TK_OK" -eq 0 ]]; then
    _STDLIB_CHECK_MODULES_WITHOUT_TK=()
    for _m in "${_STDLIB_CHECK_MODULES[@]}"; do
        [[ "$_m" == "turtle" || "$_m" == "tkinter" ]] || _STDLIB_CHECK_MODULES_WITHOUT_TK+=("$_m")
    done
    _STDLIB_CHECK_MODULES=("${_STDLIB_CHECK_MODULES_WITHOUT_TK[@]}")
fi
{
    echo "import importlib"
    echo
    echo "МОДУЛИ = ["
    for _m in "${_STDLIB_CHECK_MODULES[@]}"; do
        printf '    "%s",\n' "$_m"
    done
    echo "]"
    cat <<'PY'

def всё_на_месте():
    недоступны = []
    for имя in МОДУЛИ:
        try:
            importlib.import_module(имя)
        except Exception:
            недоступны.append(имя)
    return "ок" if not недоступны else f"нет: {', '.join(недоступны)}"
PY
} > "$_check_stdlib_py"
printf 'подключить check_stdlib\nпечать(выполнить check_stdlib.всё_на_месте())\n' > "$_check_stdlib_lu"
_check_stdlib_res="$(LU_PATH="$ROOT_DIR/build" "$ROOT_DIR/dist/lu" "$_check_stdlib_lu")"
if [[ "$_check_stdlib_res" == "ок" ]]; then
    echo "  стандартная библиотека (${#_STDLIB_CHECK_MODULES[@]} модулей) — ок"
else
    echo "  ОШИБКА: в бинарнике нет стандартных библиотек: $_check_stdlib_res" >&2
    exit 1
fi
rm -f "$_check_stdlib_py" "$_check_stdlib_lu"

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