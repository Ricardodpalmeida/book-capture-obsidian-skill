#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

run_pytest() {
    if command -v pytest >/dev/null 2>&1; then
        pytest "$@"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1 && python3 -c "import pytest" >/dev/null 2>&1; then
        python3 -m pytest "$@"
        return 0
    fi

    if command -v python >/dev/null 2>&1 && python -c "import pytest" >/dev/null 2>&1; then
        python -m pytest "$@"
        return 0
    fi

    echo "ERROR: pytest is not installed in the active Python environment." >&2
    echo "Install dev dependencies from repository root:" >&2
    echo "  pip install -r requirements-dev.txt" >&2
    echo "Then rerun: sh scripts/run_ci_local.sh" >&2
    return 2
}

echo "==> Running unit tests"
TEST_DIR="skill/book-capture-obsidian/tests"
if [ -d "$TEST_DIR" ] && find "$TEST_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) | grep -q .; then
    run_pytest -q "$TEST_DIR"
else
    echo "==> Unit tests skipped (no tests found at $TEST_DIR)"
fi

echo "==> Running script self-checks"
python3 skill/book-capture-obsidian/scripts/extract_isbn.py --self-check >/dev/null
python3 skill/book-capture-obsidian/scripts/resolve_metadata.py --self-check >/dev/null
python3 skill/book-capture-obsidian/scripts/upsert_obsidian_note.py --self-check >/dev/null
python3 skill/book-capture-obsidian/scripts/ingest_photo.py --self-check >/dev/null
python3 skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py --self-check >/dev/null
python3 skill/book-capture-obsidian/scripts/generate_dashboard.py --self-check >/dev/null

echo "==> Running security scan"
sh scripts/security_scan_no_pii.sh

echo "==> Local CI checks passed"
