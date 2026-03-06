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
6. Run validation and security checks:
   - `sh scripts/run_ci_local.sh`
   - `sh scripts/security_scan_no_pii.sh`

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
