#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SKILL_DIR="$ROOT_DIR/skill/book-capture-obsidian"
DIST_DIR="$ROOT_DIR/dist"
RUN_SECURITY_SCAN=0

if [ "${1:-}" = "--with-security-scan" ]; then
  RUN_SECURITY_SCAN=1
elif [ -n "${1:-}" ]; then
  echo "Usage: sh scripts/package_skill_local.sh [--with-security-scan]" >&2
  exit 2
fi

if [ ! -d "$SKILL_DIR" ]; then
  echo "ERROR: skill directory not found: $SKILL_DIR" >&2
  exit 2
fi

required_files="
$SKILL_DIR/SKILL.md
$SKILL_DIR/references/configuration.md
$SKILL_DIR/references/data-contracts.md
$SKILL_DIR/references/migration-runbook.md
$SKILL_DIR/references/troubleshooting.md
$SKILL_DIR/assets/templates/book-note-template.md
$SKILL_DIR/assets/templates/library-dashboard-template.md
"

for f in $required_files; do
  if [ ! -f "$f" ]; then
    echo "ERROR: required file missing: $f" >&2
    exit 2
  fi
done

if [ "$RUN_SECURITY_SCAN" -eq 1 ] && [ -f "$ROOT_DIR/scripts/security_scan_no_pii.sh" ]; then
  echo "==> Running package leak scan"
  sh "$ROOT_DIR/scripts/security_scan_no_pii.sh"
fi

mkdir -p "$DIST_DIR"

STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUT_TAR="$DIST_DIR/book-capture-obsidian-$STAMP.skill.tgz"
OUT_SHA="$OUT_TAR.sha256"

echo "==> Building local package archive"
# Non-destructive: reads source tree and emits a timestamped artifact only.
tar \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  -czf "$OUT_TAR" \
  -C "$ROOT_DIR/skill" \
  "book-capture-obsidian"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT_TAR" > "$OUT_SHA"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$OUT_TAR" > "$OUT_SHA"
else
  echo "WARNING: sha256 tool not found; checksum file not generated" >&2
fi

ls -lh "$OUT_TAR"
if [ -f "$OUT_SHA" ]; then
  cat "$OUT_SHA"
fi

echo "Package ready: $OUT_TAR"
