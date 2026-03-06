# Book Capture Obsidian Skill

Portable OpenClaw skill to capture books into Obsidian from:
- photos (barcode first, OCR fallback)
- Goodreads CSV exports

It writes deterministic Markdown notes, preserves user-written sections, and can generate a library dashboard.

## Repository Layout

- `skill/book-capture-obsidian/SKILL.md` - skill metadata + workflow
- `skill/book-capture-obsidian/scripts/` - ingestion and migration scripts
- `skill/book-capture-obsidian/references/` - contracts, config, runbooks
- `skill/book-capture-obsidian/assets/templates/` - note/dashboard templates
- `skill/book-capture-obsidian/tests/` - unit tests
- `scripts/` - CI, security scan, local packaging helper

## Dependencies

## System

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tesseract-ocr zbar-tools
```

### macOS (Homebrew)

```bash
brew update
brew install python tesseract zbar
```

## Python runtime

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Python dev/test

```bash
pip install -r requirements-dev.txt
```

`requirements.txt` includes runtime only:
- requests
- Pillow
- pyzbar
- pytesseract

`requirements-dev.txt` adds:
- pytest

## Runtime Behavior and OCR Strategy

Order of extraction:
1. `zbarimg` CLI (primary barcode)
2. `pyzbar` (secondary barcode)
3. `pytesseract` OCR fallback

If one component is missing, the pipeline degrades gracefully and continues with available stages.

## Configuration

Machine-agnostic configuration via environment variables:

```bash
export BOOK_CAPTURE_VAULT_PATH="/path/to/your/vault"
export BOOK_CAPTURE_NOTES_DIR="Library/Books"
export BOOK_CAPTURE_DASHBOARD_FILE="Library/Library Dashboard.md"

export BOOK_CAPTURE_ENABLE_ZBARIMG=true
export BOOK_CAPTURE_ENABLE_PYZBAR=true
export BOOK_CAPTURE_ENABLE_OCR=true
export BOOK_CAPTURE_OCR_LANG=eng
```

Full reference: `skill/book-capture-obsidian/references/configuration.md`

## Quickstart

## 1) Self-check scripts

```bash
python skill/book-capture-obsidian/scripts/extract_isbn.py --self-check
python skill/book-capture-obsidian/scripts/resolve_metadata.py --self-check
python skill/book-capture-obsidian/scripts/upsert_obsidian_note.py --self-check
python skill/book-capture-obsidian/scripts/ingest_photo.py --self-check
python skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py --self-check
python skill/book-capture-obsidian/scripts/generate_dashboard.py --self-check
```

## 2) Ingest a photo into Obsidian

```bash
python skill/book-capture-obsidian/scripts/ingest_photo.py \
  --image ./input/book-photo.jpg \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR"
```

## 3) Migrate Goodreads CSV (dry run first)

```bash
python skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py \
  --csv ./input/goodreads_library_export.csv \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR" \
  --dry-run
```

Live migration:

```bash
python skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py \
  --csv ./input/goodreads_library_export.csv \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR"
```

## 4) Generate or refresh dashboard

```bash
python skill/book-capture-obsidian/scripts/generate_dashboard.py \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR" \
  --dashboard-file "$BOOK_CAPTURE_DASHBOARD_FILE"
```

## QA and Security

Run local CI:

```bash
sh scripts/run_ci_local.sh
```

Run only privacy/security scan:

```bash
sh scripts/security_scan_no_pii.sh
```

## Privacy and Safety Defaults

- No machine-specific paths required
- No secret storage in notes/templates/config
- No raw image retention by default
- No outbound writes except metadata API reads (Open Library / Google Books)

## Packaging

Local package helper:

```bash
sh scripts/package_skill_local.sh --with-security-scan
```

This creates `dist/book-capture-obsidian-<timestamp>.skill.tgz` plus checksum.

## Publish Targets

- GitHub public repository
- ClawHub skill publication

Use `RELEASE_READINESS.md` checklist before publishing.
