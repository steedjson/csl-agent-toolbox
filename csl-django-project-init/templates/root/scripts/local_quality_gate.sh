#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

VENV_BIN="$ROOT_DIR/.venv/bin"
PYTHON_FILES=()

collect_changed_python_files() {
    {
        git diff --name-only --diff-filter=ACMR HEAD -- '*.py'
        git ls-files --others --exclude-standard -- '*.py'
    } | sort -u
}

while IFS= read -r file; do
    case "$file" in
        */migrations/*|*/__pycache__/*|*settings_local.py|*.example.py)
            continue
            ;;
    esac
    PYTHON_FILES+=("$file")
done < <(collect_changed_python_files)

require_tool() {
    if [[ ! -x "$1" ]]; then
        echo "缺少开发工具：$1" >&2
        echo "请先运行 make install-dev。" >&2
        exit 2
    fi
}

require_python_tools() {
    require_tool "$VENV_BIN/black"
    require_tool "$VENV_BIN/isort"
    require_tool "$VENV_BIN/python"
}

format_changed() {
    if ((${#PYTHON_FILES[@]} == 0)); then
        echo "没有需要格式化的 Python 文件。"
        return
    fi
    "$VENV_BIN/isort" "${PYTHON_FILES[@]}"
    "$VENV_BIN/black" "${PYTHON_FILES[@]}"
}

check_format() {
    if ((${#PYTHON_FILES[@]} == 0)); then
        echo "没有需要检查格式的 Python 文件。"
        return
    fi
    "$VENV_BIN/isort" --check-only "${PYTHON_FILES[@]}"
    "$VENV_BIN/black" --check "${PYTHON_FILES[@]}"
}

lint_changed() {
    if ((${#PYTHON_FILES[@]} == 0)); then
        echo "没有需要执行 Pylint 的 Python 文件。"
        return
    fi
    "$VENV_BIN/python" -m pylint "${PYTHON_FILES[@]}" --errors-only --score=no
}

run_focused_tests() {
    if ((${#PYTHON_FILES[@]} > 0)) && (($# == 0)); then
        echo "检测到 Python 变更，请通过 TEST 指定目标测试，例如：" >&2
        echo "  make verify TEST=apps/admin/salary/tests/test_salary_api.py" >&2
        exit 2
    fi
    if (($# > 0)); then
        require_tool "$VENV_BIN/pytest"
        "$VENV_BIN/pytest" -q "$@"
    fi
}

run_diff_checks() {
    git diff HEAD --check
    git diff HEAD --stat
}

MODE=${1:-check}
shift || true

case "$MODE" in
    format)
        require_python_tools
        format_changed
        ;;
    lint)
        require_python_tools
        lint_changed
        ;;
    check)
        require_python_tools
        check_format
        lint_changed
        run_diff_checks
        ;;
    verify)
        require_python_tools
        format_changed
        lint_changed
        run_focused_tests "$@"
        run_diff_checks
        ;;
    full)
        require_python_tools
        require_tool "$VENV_BIN/pytest"
        format_changed
        lint_changed
        "$VENV_BIN/pytest" -q
        run_diff_checks
        ;;
    *)
        echo "用法：$0 {format|lint|check|verify|full} [pytest targets...]" >&2
        exit 2
        ;;
esac
