# Book Capture for Obsidian

Turn photos, barcodes, ISBNs, titles or Goodreads CSV exports into Obsidian book notes and a Dataview dashboard. Choose **Google Books only**, **Open Library only**, or both in either order. Re-runs preserve `## User Notes` and update matching books without deleting notes.

Install: `openclaw skills install @ricardodpalmeida/book-capture-obsidian`. [ClawHub](https://clawhub.ai/ricardodpalmeida/book-capture-obsidian) · [Changes](CHANGELOG.md)

## Requirements and setup

Python 3.10+ and an existing vault. Installed skill: `sh <skill>/scripts/setup.sh` creates its own environment and installs runtime dependencies. Windows instructions and all settings: [configuration](skill/book-capture-obsidian/references/configuration.md).

From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Photo extraction additionally uses zbar and/or Tesseract: Debian/Ubuntu packages `zbar-tools tesseract-ocr`; Homebrew `zbar tesseract`. Run `extract_isbn.py --diagnose-deps` first. Extraction tries `zbarimg`, `pyzbar`, `pytesseract`, then the Tesseract CLI; missing components are skipped. ISBN/title and CSV workflows do not require OCR.

## Choose metadata provider

| `BOOK_CAPTURE_METADATA_PROVIDER_ORDER` | Behavior |
| --- | --- |
| `google_books` | Google only, even on misses or quota errors |
| `openlibrary` | Open Library only |
| `google_books,openlibrary` | Google first; Open Library fills gaps |
| `openlibrary,google_books` | Default; Open Library first, Google fills gaps |

For Google, enable Books API in your Cloud project and privately supply `BOOK_CAPTURE_GOOGLE_API_KEY`. Paid Cloud billing does not guarantee extra Books quota. [Requirements and quota handling](skill/book-capture-obsidian/references/configuration.md#metadata-providers-and-api-requirements) explain restrictions, quota checks/increase requests, pacing and resumable imports.

All workflows share provider selection and caching. Google defaults to one second between attempts, 100 attempts per run including retries, and a persisted pause on rate/quota errors. Long server backoff is respected. Limits are configurable per run; they do not replace the project's quota. Open Library is keyless but rate limited. Trusted input fields are retained.

## Use

`PY` below means the selected environment's Python. Replace paths with your files:

```bash
PY skill/book-capture-obsidian/scripts/ingest_photo.py --image book.jpg --vault-path /path/to/vault
PY skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py --csv export.csv --vault-path /path/to/vault --dry-run
PY skill/book-capture-obsidian/scripts/generate_dashboard.py --vault-path /path/to/vault
```

Inspect the dry-run counts/errors, then omit `--dry-run` to import. For large exports, use a small batch first or `--no-enrich` for local CSV-only import. Full workflows: [SKILL.md](skill/book-capture-obsidian/SKILL.md); [migration runbook](skill/book-capture-obsidian/references/migration-runbook.md).

Read JSON `ok`, `error` and `warnings` before treating a run as successful. Notes match by ISBN or Goodreads ID and may be renamed/refiled. Keep personal content below `## User Notes`; generated content above it is replaced. Dashboard tables need Obsidian Dataview.

## Privacy and maintenance

Only ISBN/title/author queries go to selected metadata APIs. Scripts leave source photos in place, never upload photos or vault contents, and redact the Google key from returned metadata/errors. Obsidian may fetch remote cover images.

The installable skill contains `scripts/`, `references/`, `assets/templates/` and `tests/`. Root `scripts/` contains CI, privacy scans and packaging helpers:

```bash
pip install -r requirements-dev.txt
sh scripts/run_ci_local.sh
sh scripts/package_skill_local.sh --with-security-scan
```

The package helper writes `dist/book-capture-obsidian-<timestamp>.skill.tgz` with a checksum. Use [RELEASE_READINESS.md](RELEASE_READINESS.md) before publishing.

[MIT-0](LICENSE).

## More from the author

Made by Ricardo Pacheco Almeida. I write about applied AI, agents and enterprise architecture at [ricbits](https://me.ricbits.cc).

| Skill | What it does |
|-------|--------------|
| [whetstone](https://github.com/Ricardodpalmeida/whetstone) | Reviews consequential code changes with checks proportional to their impact. |
| [LadybugDB openCypher](https://clawhub.ai/ricardodpalmeida/ladybug-opencypher-updated) | Design and query LadybugDB graphs with openCypher, including imports, full-text search and Neo4j query adaptation. |
| [Microsoft Learn MCP](https://clawhub.ai/ricardodpalmeida/mslearn-mcp) | Grounds Azure, .NET, Microsoft 365 and Power Platform answers in official Microsoft Learn docs. |
| [Excalidraw Diagrams for Obsidian](https://clawhub.ai/ricardodpalmeida/excalidraw-diagrams) | Turns boxes and arrows into clean, hand-drawn Excalidraw diagrams for Obsidian or excalidraw.com. |
