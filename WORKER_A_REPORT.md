# WORKER_A_REPORT

## Scope Delivered
Implemented Worker A core ingestion engine in the allowed files only:

- `skill/book-capture-obsidian/scripts/common_json.py`
- `skill/book-capture-obsidian/scripts/common_config.py`
- `skill/book-capture-obsidian/scripts/common_isbn.py`
- `skill/book-capture-obsidian/scripts/extract_isbn.py`
- `skill/book-capture-obsidian/scripts/resolve_metadata.py`
- `skill/book-capture-obsidian/scripts/upsert_obsidian_note.py`
- `skill/book-capture-obsidian/scripts/ingest_photo.py`
- `requirements.txt`

## What Was Built

### 1) Barcode-first ISBN extraction with OCR fallback
`extract_isbn.py` now implements the required strategy:

1. Barcode pass via `zbarimg` (configurable binary/path and timeout)
2. Barcode pass via `pyzbar`
3. OCR fallback via `pytesseract` only if barcode passes fail

It emits deterministic JSON with standardized envelope:
- `stage`, `ok`, `error`
- `source_image`, `method`, `isbn13`, `isbn_candidates`, `warnings`

### 2) Portable configuration via env vars (safe defaults)
No hardcoded machine paths were added. Config is env-driven with defaults, including:

- `BOOK_CAPTURE_ENABLE_ZBARIMG` (default true)
- `BOOK_CAPTURE_ZBARIMG_BIN` (default `zbarimg`)
- `BOOK_CAPTURE_ZBARIMG_TIMEOUT_SECONDS` (default `8`)
- `BOOK_CAPTURE_ENABLE_PYZBAR` (default true)
- `BOOK_CAPTURE_ENABLE_OCR` (default true)
- `BOOK_CAPTURE_OCR_LANG` (default `eng`)
- `BOOK_CAPTURE_TESSERACT_CMD` (default empty)
- `BOOK_CAPTURE_HTTP_TIMEOUT_SECONDS` (default `12`)
- `BOOK_CAPTURE_USER_AGENT` (default `book-capture-obsidian/1.0`)
- `BOOK_CAPTURE_METADATA_PROVIDER_ORDER` (default `google_books,openlibrary`)
- `BOOK_CAPTURE_VAULT_PATH` (default `.`)
- `BOOK_CAPTURE_NOTES_DIR` (default `Books`)
- `BOOK_CAPTURE_TARGET_NOTE` (default empty)

### 3) Deterministic JSON contracts across scripts
All scripts use a shared contract envelope (`common_json.py`) and deterministic output (`sort_keys=True`):

- `extract_isbn.py`
- `resolve_metadata.py`
- `upsert_obsidian_note.py`
- `ingest_photo.py`

### 4) Metadata resolution engine
`resolve_metadata.py` resolves metadata from ISBN with provider order and fallback:
- Google Books API
- Open Library API

It normalizes provider outputs into one stable schema (`title`, `authors`, `publisher`, `published_date`, `description`, `page_count`, `language`, `categories`, `cover_image`, `source`, `source_url`).

### 5) Idempotent Obsidian note upsert preserving user content
`upsert_obsidian_note.py` supports:
- create/update deterministic auto-managed block
- marker-based replacement preserving user-written content outside markers
- safe behavior when file has no markers (prepend auto block, keep existing body)
- idempotent writes (`updated=false` if no content change)
- flexible call signatures for compatibility (`upsert_note(payload, ...)`, `upsert_note(note_path, payload)`, `upsert_note(payload, note_path)`, keyword legacy aliases)

Markers used:
- `<!-- BOOK_CAPTURE:BEGIN AUTO -->`
- `<!-- BOOK_CAPTURE:END AUTO -->`

### 6) End-to-end orchestrator
`ingest_photo.py` runs:
1. extract ISBN
2. resolve metadata
3. upsert Obsidian note

Returns a single deterministic JSON payload with nested stage results.

### 7) Minimal dependencies
`requirements.txt` created with minimal runtime deps:
- `requests`
- `Pillow`
- `pyzbar`
- `pytesseract`

Optional system dependencies (auto-detected at runtime, graceful fallback when missing):
- `zbarimg` CLI for primary barcode scan
- `zbar` shared library used by `pyzbar`
- `tesseract` binary for OCR fallback

## Validation / Self-check Commands Passed
Executed successfully from repo root:

1. `python3 skill/book-capture-obsidian/scripts/extract_isbn.py --self-check`
2. `python3 skill/book-capture-obsidian/scripts/resolve_metadata.py --self-check`
3. `python3 skill/book-capture-obsidian/scripts/upsert_obsidian_note.py --self-check`
4. `python3 skill/book-capture-obsidian/scripts/ingest_photo.py --self-check`
5. `python3 -m py_compile skill/book-capture-obsidian/scripts/common_config.py skill/book-capture-obsidian/scripts/common_isbn.py skill/book-capture-obsidian/scripts/common_json.py skill/book-capture-obsidian/scripts/extract_isbn.py skill/book-capture-obsidian/scripts/resolve_metadata.py skill/book-capture-obsidian/scripts/upsert_obsidian_note.py skill/book-capture-obsidian/scripts/ingest_photo.py`
6. Idempotency check (temp vault, two consecutive upserts) with assertion `run2.updated == false` and `run2.created == false`
7. Legacy-signature idempotency check matching common test harness call style: `upsert_note(note_path, payload)` twice with same payload, asserting unchanged file and single ISBN occurrence
8. Error-path contract check: `python3 skill/book-capture-obsidian/scripts/ingest_photo.py --image missing-image.jpg` returns deterministic JSON failure envelope with nested `extract` stage details and exit code `1`

9. Privacy scan check across Worker A deliverables for sensitive identifiers and user-specific absolute paths (no matches)

All above checks passed.
