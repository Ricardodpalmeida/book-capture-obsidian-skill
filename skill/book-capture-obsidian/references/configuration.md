# Configuration

Every setting is an environment variable; command-line flags win where both exist. Nothing is machine-specific by default.

## Paths

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOOK_CAPTURE_VAULT_PATH` | none (required) | Obsidian vault root. Scripts refuse to write without an existing directory. |
| `BOOK_CAPTURE_NOTES_DIR` | `Books` | Folder for book notes, relative to the vault. |
| `BOOK_CAPTURE_DASHBOARD_FILE` | `<notes dir>/Library Dashboard.md` | Dashboard note, relative to the vault. |
| `BOOK_CAPTURE_DASHBOARD_TEMPLATE` | the skill's `assets/templates/library-dashboard-template.md` | Custom dashboard template. |
| `BOOK_CAPTURE_TARGET_NOTE` | none | Write one capture to this exact note path (must be inside the vault). |
| `BOOK_CAPTURE_RELATED_DIRS` | none | Comma-separated vault folders to search for related notes, besides the books folder. |

## Notes

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOOK_CAPTURE_NOTE_LANGUAGE` | `en` | `pt` writes `## Sinopse` and Portuguese fallback text; anything else writes English. |
| `BOOK_CAPTURE_GROUP_BY_SHELF` | `false` | Goodreads import files notes in one subfolder per shelf. |
| `BOOK_CAPTURE_SHELVES_TO_READ` | `to-read,want-to-read,tbr` | Shelves counted as "to read" on the dashboard. |
| `BOOK_CAPTURE_SHELVES_READING` | `currently-reading,reading` | Shelves counted as "reading". |
| `BOOK_CAPTURE_SHELVES_READ` | `read,finished` | Shelves counted as "read". |

## Metadata lookups

Open Library is free and keyless. Google Books without a key shares a small anonymous quota per IP address, which is why bulk imports used to fail with HTTP 429. The resolver now protects that quota in four ways: Open Library goes first, Google only fills fields that are still empty, every answer is cached, and a 429 pauses Google instead of retrying it row after row.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOOK_CAPTURE_METADATA_PROVIDER_ORDER` | `openlibrary,google_books` | Lookup order. Later providers only fill gaps. |
| `BOOK_CAPTURE_ENABLE_ENRICH` | `true` | `false` makes Goodreads imports use only the CSV data. The old name `BOOK_CAPTURE_ENABLE_GOOGLE_ENRICH` still works. |
| `BOOK_CAPTURE_GOOGLE_API_KEY` | none | Google Books API key (free in Google Cloud). Raises the quota a lot. Never written to notes or output. |
| `BOOK_CAPTURE_GOOGLE_MAX_REQUESTS_PER_RUN` | `100` | Hard cap on Google requests in one script run. |
| `BOOK_CAPTURE_GOOGLE_COOLDOWN_SECONDS` | `3600` | After a 429, Google is skipped for this long, across runs. |
| `BOOK_CAPTURE_GOOGLE_MAX_RETRIES` | `2` | Retries for network errors, 429 and 5xx before giving up. |
| `BOOK_CAPTURE_GOOGLE_DELAY_MS` | `400` | Base backoff between retries (doubles each time). |
| `BOOK_CAPTURE_GOOGLE_MAX_RETRY_AFTER_SECONDS` | `10` | Upper bound on any single wait. |
| `BOOK_CAPTURE_OPENLIBRARY_DELAY_MS` | `350` | Minimum gap between Open Library requests. |
| `BOOK_CAPTURE_HTTP_TIMEOUT_SECONDS` | `12` | Per-request timeout. |
| `BOOK_CAPTURE_USER_AGENT` | `book-capture-obsidian/1.3 (+repo URL)` | Sent to both APIs; Open Library asks clients to identify themselves. |
| `BOOK_CAPTURE_CACHE` | `on` | `off` keeps the cache in memory for the current run only. |
| `BOOK_CAPTURE_CACHE_DIR` | `$XDG_CACHE_HOME/book-capture-obsidian` or `~/.cache/book-capture-obsidian` | Where `metadata.sqlite3` lives. Deleting it is safe. |

Found books are cached for 180 days and "not found" answers for 14 days. Network errors, 5xx responses and rate limits are never cached.

## Photo extraction

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOOK_CAPTURE_ENABLE_ZBARIMG` | `true` | Use the `zbarimg` CLI for barcodes. |
| `BOOK_CAPTURE_ZBARIMG_BIN` | `zbarimg` | Path to `zbarimg`. |
| `BOOK_CAPTURE_ZBARIMG_TIMEOUT_SECONDS` | `8` | Barcode timeout. |
| `BOOK_CAPTURE_ENABLE_PYZBAR` | `true` | Use the `pyzbar` library as a second barcode reader. |
| `BOOK_CAPTURE_ENABLE_OCR` | `true` | Fall back to OCR when no barcode is found. |
| `BOOK_CAPTURE_OCR_LANG` | `eng` | Tesseract language codes, for example `eng+por`. |
| `BOOK_CAPTURE_TESSERACT_CMD` | auto | Path to the `tesseract` binary. |
| `BOOK_CAPTURE_TESSERACT_TIMEOUT_SECONDS` | `20` | OCR timeout. |

Missing components degrade in order: `zbarimg`, then `pyzbar`, then `pytesseract`, then the `tesseract` CLI. With none available the result is a deterministic extraction failure.

## Privacy

Raw photos are not copied or kept. Only normalized metadata and Markdown are written. Keys are sent as request parameters to Google only and are redacted from every result and warning.
