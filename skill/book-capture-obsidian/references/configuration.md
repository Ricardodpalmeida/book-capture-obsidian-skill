# Configuration

This skill is machine-agnostic by design.
Configure paths and behavior with environment variables.

## Core Paths

Use `--vault-path` on commands, or set `BOOK_CAPTURE_VAULT_PATH` as a default.
At least one of them is required for migration commands.

```bash
export BOOK_CAPTURE_VAULT_PATH="/path/to/obsidian-vault"
export BOOK_CAPTURE_NOTES_DIR="6. Library"
export BOOK_CAPTURE_DASHBOARD_FILE="6. Library/Library Dashboard.md"
```

Optional explicit note target for one-off writes:

```bash
export BOOK_CAPTURE_TARGET_NOTE="/path/to/obsidian-vault/6. Library/Book Title - Author (Publisher, 2025).md"
```

## Goodreads Migration Controls

```bash
# Enrich all rows with Google Books by default
export BOOK_CAPTURE_ENABLE_GOOGLE_ENRICH=true

# Optional dedicated Google Books API key (recommended for stable quota)
export BOOK_CAPTURE_GOOGLE_API_KEY="YOUR_GOOGLE_BOOKS_API_KEY"

# Delay and retry controls for Google API rate limits
export BOOK_CAPTURE_GOOGLE_DELAY_MS=400
export BOOK_CAPTURE_GOOGLE_MAX_RETRIES=5
export BOOK_CAPTURE_GOOGLE_MAX_RETRY_AFTER_SECONDS=10

# Optional folder structure by shelf property
export BOOK_CAPTURE_GROUP_BY_SHELF=true
```

## Extraction Controls

```bash
export BOOK_CAPTURE_ENABLE_ZBARIMG=true
export BOOK_CAPTURE_ZBARIMG_BIN=zbarimg
export BOOK_CAPTURE_ZBARIMG_TIMEOUT_SECONDS=8

export BOOK_CAPTURE_ENABLE_PYZBAR=true
export BOOK_CAPTURE_ENABLE_OCR=true
export BOOK_CAPTURE_OCR_LANG=eng
export BOOK_CAPTURE_TESSERACT_TIMEOUT_SECONDS=20
# Optional explicit tesseract binary path:
# export BOOK_CAPTURE_TESSERACT_CMD=/path/to/tesseract
```

## Metadata Resolver Controls

```bash
export BOOK_CAPTURE_METADATA_PROVIDER_ORDER="google_books,openlibrary"
export BOOK_CAPTURE_HTTP_TIMEOUT_SECONDS=12
export BOOK_CAPTURE_USER_AGENT="book-capture-obsidian/1.0"
```

## Dashboard Template Override

```bash
export BOOK_CAPTURE_DASHBOARD_TEMPLATE="skill/book-capture-obsidian/assets/templates/library-dashboard-template.md"
```

## Defaults and Fallbacks

- Barcode primary: `zbarimg`
- Barcode secondary: `pyzbar`
- OCR fallback: `pytesseract`, then direct `tesseract` CLI when the wrapper is unavailable
- Photo and Goodreads enrichment: one keyed Google Books client with bounded retries

Behavior:
- Missing `zbarimg` -> continue with `pyzbar` and/or OCR.
- Missing `pyzbar` -> continue with `zbarimg` and/or OCR.
- Missing `pytesseract` -> use the installed `tesseract` binary directly.
- Missing both OCR paths -> barcode-only mode.
- Google network, rate-limit, or transient server failure -> retry within configured bounds, then continue to the next metadata provider.
- No barcode and no OCR -> deterministic extraction failure JSON.

The Google key is sent as an HTTP parameter and is never included in result JSON or warnings. Google Books requests use a partial-response field set to reduce response volume.

## Privacy Defaults

- Do not store secrets or credentials in notes/config.
- Do not retain raw photos by default.
- Persist only normalized metadata and Markdown output.
