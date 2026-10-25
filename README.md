# 📚 Book Capture for Obsidian

**Snap a cover, scan a barcode or drop in your Goodreads export, and get clean, linked book notes in Obsidian, plus a live library dashboard.**

An OpenClaw skill that does the boring parts of keeping a reading library:

- **Any input.** A cover or barcode photo (barcode first, OCR fallback), an ISBN, a title, or a whole Goodreads CSV.
- **Quota-safe metadata.** Open Library first, a local cache, and Google Books only to fill gaps, with a per-run budget and an automatic pause after a rate limit. Re-running a 600-book import costs no API calls.
- **Your notes stay yours.** Re-runs refresh metadata and never touch `## User Notes`. Nothing is ever deleted.
- **A dashboard that keeps up.** Dataview views of what you are reading, what is next and what you finished, by shelf.

```bash
openclaw skills install @ricardodpalmeida/book-capture-obsidian
```

On ClawHub: [book-capture-obsidian](https://clawhub.ai/ricardodpalmeida/book-capture-obsidian). Changes are in [CHANGELOG.md](CHANGELOG.md).

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

Installed skill: `sh <skill>/scripts/setup.sh` creates `<skill>/.venv` and installs the runtime packages.

From a repository checkout:

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
3. `pytesseract` OCR
4. Direct `tesseract` CLI when `pytesseract` is unavailable

If one component is missing, the pipeline degrades gracefully and continues with available stages.

Photo capture and Goodreads import share one quota-aware metadata resolver. Open Library is queried first; Google Books only fills fields that are still empty. Answers are cached in `~/.cache/book-capture-obsidian/metadata.sqlite3` (180 days for hits, 14 for misses), Google is capped at 100 requests per run, and an HTTP 429 pauses Google for an hour across runs instead of retrying every row. A Goodreads dry run makes no network calls. Set `BOOK_CAPTURE_GOOGLE_API_KEY` for a much larger Google quota.

## Configuration

Machine-agnostic configuration via environment variables:

```bash
export BOOK_CAPTURE_VAULT_PATH="/path/to/your/vault"   # required; scripts refuse to write without it
export BOOK_CAPTURE_NOTES_DIR="Books"                  # default
export BOOK_CAPTURE_NOTE_LANGUAGE="en"                 # or "pt" for Portuguese headings
export BOOK_CAPTURE_GOOGLE_API_KEY="..."               # optional
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

Try a small live batch with `--limit 20`, then run the full migration:

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
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR"
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

## License

[MIT-0](LICENSE) (MIT No Attribution): use, copy, modify and redistribute it for any purpose, with no attribution required. The same license applies on ClawHub.

## More from the author

Made by Ricardo Pacheco Almeida. I write about applied AI, agents and enterprise architecture at [ricbits](https://me.ricbits.cc).

| Skill | What it does |
|-------|--------------|
| [whetstone](https://github.com/Ricardodpalmeida/whetstone) | Makes a coding agent size every change by risk before it touches anything, then scale the process to match. |
| [LadybugDB openCypher](https://clawhub.ai/ricardodpalmeida/ladybug-opencypher-updated) | Design and query LadybugDB graphs with openCypher, including imports, full-text search and Neo4j query adaptation. |
| [Microsoft Learn MCP](https://clawhub.ai/ricardodpalmeida/mslearn-mcp) | Grounds Azure, .NET, Microsoft 365 and Power Platform answers in official Microsoft Learn docs. |
| [Excalidraw Diagrams for Obsidian](https://clawhub.ai/ricardodpalmeida/excalidraw-diagrams) | Turns boxes and arrows into clean, hand-drawn Excalidraw diagrams for Obsidian or excalidraw.com. |
