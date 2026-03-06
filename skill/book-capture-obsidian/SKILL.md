---
name: book-capture-obsidian
description: Capture and normalize book metadata into Obsidian Markdown notes from photos or Goodreads CSV exports. Use for barcode and OCR ISBN extraction, metadata enrichment, idempotent note upsert, bulk migration, and dashboard generation.
---

# Book Capture Obsidian

Execute this workflow to add or migrate books into an Obsidian vault.

## Workflow

1. Read `references/configuration.md` and set environment variables.
2. Choose one mode:
   - Photo ingest with `scripts/ingest_photo.py`
   - Goodreads CSV migration with `scripts/migrate_goodreads_csv.py`
3. Resolve metadata using the provider chain in `scripts/resolve_metadata.py`.
4. Upsert notes with `scripts/upsert_obsidian_note.py`.
5. Refresh the dashboard with `scripts/generate_dashboard.py`.
6. Run packaged validation checks:
   - `python3 -m pytest -q tests` (optional, requires `pytest`)
   - `python3 scripts/extract_isbn.py --self-check`
   - `python3 scripts/resolve_metadata.py --self-check`
   - `python3 scripts/upsert_obsidian_note.py --self-check`
   - `python3 scripts/ingest_photo.py --self-check`
   - `python3 scripts/migrate_goodreads_csv.py --self-check`
   - `python3 scripts/generate_dashboard.py --self-check`

## Required References

- `references/configuration.md` for runtime settings and portability
- `references/data-contracts.md` for normalized schema and output contracts
- `references/migration-runbook.md` for Goodreads import sequence
- `references/troubleshooting.md` for extraction and merge failures

## Operating Rules

- Prefer barcode extraction first; use OCR as fallback.
- Never hardcode machine-specific paths.
- Preserve user-written content outside auto-managed note block.
- Keep outputs deterministic and idempotent for repeated runs.
- Do not store secrets or personal identifiers in generated artifacts.
