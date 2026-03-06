# Goodreads CSV Migration Runbook

Use this runbook to migrate Goodreads exports into Obsidian notes safely.

## Input

- Goodreads CSV export file
- Configured vault path (`BOOK_CAPTURE_VAULT_PATH`)
- Configured notes dir (`BOOK_CAPTURE_NOTES_DIR`)

## Preflight

1. Ensure CSV is UTF-8 (`utf-8-sig` is accepted).
2. Ensure required columns exist:
   - `Title`, `Author`, `ISBN`, `ISBN13`, `Exclusive Shelf`
3. Install dependencies (`requirements.txt` + `requirements-dev.txt` for tests).
4. Run security scan before release packaging:
   - `sh scripts/security_scan_no_pii.sh`

## Dry Run First

```bash
python skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py \
  --csv ./input/goodreads_library_export.csv \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR" \
  --dry-run
```

Review output stats and row-level errors.

## Live Migration

```bash
python skill/book-capture-obsidian/scripts/migrate_goodreads_csv.py \
  --csv ./input/goodreads_library_export.csv \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR"
```

## Mapping Rules

- `Title` -> `metadata.title`
- `Author` -> `metadata.authors[0]`
- `ISBN13` / `ISBN` -> canonical `isbn13`
- `Exclusive Shelf` -> `status`
- `My Rating` -> `rating`
- `Date Read` -> `finished`
- `Bookshelves` -> `tags` and `metadata.categories`

Status mapping:
- `to-read` -> `to-read`
- `currently-reading` -> `reading`
- `read` -> `finished`
- `did-not-finish` -> `dnf`
- unknown -> `inbox`

## Dedup Strategy

- Primary: ISBN-13
- If note already exists for ISBN, perform idempotent update
- Preserve user-written sections outside auto-managed block

## Post Migration

1. Refresh dashboard:

```bash
python skill/book-capture-obsidian/scripts/generate_dashboard.py \
  --vault-path "$BOOK_CAPTURE_VAULT_PATH" \
  --notes-dir "$BOOK_CAPTURE_NOTES_DIR" \
  --dashboard-file "$BOOK_CAPTURE_DASHBOARD_FILE"
```

2. Validate random sample notes for metadata quality.
3. Resolve rows skipped due to missing/invalid ISBN manually.
