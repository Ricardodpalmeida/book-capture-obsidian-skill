---
name: book-capture-obsidian
description: "Add books to an Obsidian vault as notes: from a photo of the cover or barcode, from an ISBN or title, or in bulk from a Goodreads CSV export, then refresh a library dashboard. Use when the user wants to catalogue, log or import books into Obsidian."
homepage: https://github.com/Ricardodpalmeida/book-capture-obsidian-skill
metadata:
  {
    "openclaw":
      {
        "emoji": "📚",
        "requires": { "bins": ["python3"] },
        "homepage": "https://github.com/Ricardodpalmeida/book-capture-obsidian-skill",
      },
  }
---

# Book Capture Obsidian

Turn a book photo, an ISBN, a title or a Goodreads export into Obsidian notes with clean frontmatter, then keep a dashboard up to date. Every script prints one JSON object; read `ok`, `error` and `warnings` before telling the user anything.

## Setup (once per machine)

Run `sh {baseDir}/scripts/setup.sh`. It creates `{baseDir}/.venv` and installs the Python packages. Use `{baseDir}/.venv/bin/python` for every command below (written as `PY`). For photos, the host also needs `zbarimg` (zbar-tools) or `tesseract`; `PY {baseDir}/scripts/extract_isbn.py --diagnose-deps` shows what is available.

The vault path is mandatory: ask the user for it if `BOOK_CAPTURE_VAULT_PATH` is not set, and never guess it. Scripts refuse to write without an existing vault directory.

## Workflows

**One book from a photo.** `PY {baseDir}/scripts/ingest_photo.py --image <file> --vault-path <vault> [--shelf to-read]`. Barcode first, OCR fallback. If no ISBN is found, ask the user for the title or ISBN instead of retrying the photo.

**One book from an ISBN or title.** `PY {baseDir}/scripts/resolve_metadata.py --isbn <isbn>` (or `--title "<title>" --author "<author>"`) writes the metadata JSON to stdout; save it to a temp file and pass it to `PY {baseDir}/scripts/upsert_obsidian_note.py --metadata-json <file> --vault-path <vault>`. Add `"shelf": "<name>"` to that JSON to file the note on a shelf.

**Goodreads import.** Always dry-run first: `PY {baseDir}/scripts/migrate_goodreads_csv.py --csv <file> --vault-path <vault> --dry-run`. A dry run makes no network calls. Show the user the counts, then run without `--dry-run`. For a first try on a large export, add `--limit 20`. Read `references/migration-runbook.md` before a large import.

**Dashboard.** `PY {baseDir}/scripts/generate_dashboard.py --vault-path <vault>` after any import.

## Metadata lookups and API quotas

Open Library is queried first (no key, no daily quota). Google Books only fills fields that are still missing. Results are cached on disk for 180 days, so re-running an import costs no API calls. Google gets at most 100 requests per run, and a rate-limit response pauses it for an hour across runs. When the JSON reports `google_books skipped` or `paused`, the notes are still written with Open Library data; tell the user, and suggest setting `BOOK_CAPTURE_GOOGLE_API_KEY` if they want richer descriptions. Settings: `references/configuration.md`.

## Rules

- Write only inside the vault the user named. Never delete notes; the scripts move a note only to rename it.
- Re-running is safe: notes are matched by ISBN (or Goodreads Book Id) and the `## User Notes` section is always preserved.
- Do not store API keys in notes, JSON files or chat replies.
- When something fails, check `references/troubleshooting.md` before changing settings.
