# Configuration

Every setting is an environment variable; command-line flags win where both exist. Nothing is machine-specific by default.

## Windows setup

Use Python 3.10+ in a skill-local environment:

```powershell
python -m venv "<skill>/.venv"
& "<skill>/.venv/Scripts/python.exe" -m pip install -r "<skill>/requirements.txt"
```

Use that interpreter as `PY` in the workflows. Photo extraction also needs the selected barcode/OCR runtime; diagnose before installing missing components.

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

Open Library is keyless but rate limited: the default one-second gap follows its [unidentified-client limit](https://openlibrary.org/developers/api). Identified clients with contact details may use its higher limit. Google fills gaps; a per-run HTTP-attempt budget, cache and persisted cooldown reduce quota use.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOOK_CAPTURE_METADATA_PROVIDER_ORDER` | `openlibrary,google_books` | Lookup order. Later providers only fill gaps. |
| `BOOK_CAPTURE_ENABLE_ENRICH` | `true` | `false` makes Goodreads imports use only the CSV data. The old name `BOOK_CAPTURE_ENABLE_GOOGLE_ENRICH` still works. |
| `BOOK_CAPTURE_GOOGLE_API_KEY` | none | Optional Google Books project key. Quota depends on that project; extra capacity is not guaranteed. Redacted from results. |
| `BOOK_CAPTURE_GOOGLE_MAX_REQUESTS_PER_RUN` | `100` | Maximum HTTP attempts per run, including retries. |
| `BOOK_CAPTURE_GOOGLE_COOLDOWN_SECONDS` | `3600` | After exhausted 429 retries, skip Google for this long across runs. |
| `BOOK_CAPTURE_GOOGLE_MAX_RETRIES` | `2` | Retries for network errors, 429 and 5xx before giving up. |
| `BOOK_CAPTURE_GOOGLE_DELAY_MS` | `400` | Base backoff between retries (doubles each time). |
| `BOOK_CAPTURE_GOOGLE_MAX_RETRY_AFTER_SECONDS` | `10` | Upper bound on any single wait. |
| `BOOK_CAPTURE_OPENLIBRARY_DELAY_MS` | `1000` | Minimum gap between Open Library requests. |
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

Scripts leave source photos in place; they do not upload or copy them. They store metadata/cache and Markdown. API keys go only to Google as request parameters and are redacted from outputs. Obsidian may fetch remote covers when displaying notes.
