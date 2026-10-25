# Goodreads CSV Migration Runbook

Import a Goodreads library export into Obsidian notes without burning API quota or duplicating notes.

## Input

- The Goodreads export (My Books, then Import and export, then Export Library). UTF-8, with or without BOM.
- Columns used: `Book Id`, `Title`, `Author`, `ISBN`, `ISBN13`, `Publisher`, `Year Published`, `Exclusive Shelf`, `Bookshelves`. Only `Title` is mandatory.
- An existing vault directory.

## 1. Dry run (no network, no writes)

```bash
PY {baseDir}/scripts/migrate_goodreads_csv.py --csv export.csv --vault-path "$VAULT" --dry-run
```

Check `stats.skipped` and `errors`. A dry run never calls Open Library or Google Books, so it can be repeated freely.

## 2. Small live batch

```bash
PY {baseDir}/scripts/migrate_goodreads_csv.py --csv export.csv --vault-path "$VAULT" --limit 20
```

Open two or three notes in Obsidian and check them before importing everything. `enrichment.stats` shows how many lookups hit the network, how many came from the cache, and whether Google was skipped.

## 3. Full import

```bash
PY {baseDir}/scripts/migrate_goodreads_csv.py --csv export.csv --vault-path "$VAULT" [--group-by-shelf]
```

The rows already imported in step 2 are served from the cache. If Google hits its quota, the run continues with Open Library data and reports `google_books skipped` in `enrichment.warnings`. Re-run the same command later (after the cooldown, or with `BOOK_CAPTURE_GOOGLE_API_KEY` set) to fill the gaps; existing notes are updated in place.

Use `--no-enrich` to import only what the CSV contains.

## 4. Dashboard

```bash
PY {baseDir}/scripts/generate_dashboard.py --vault-path "$VAULT"
```

## Mapping

| Goodreads column | Note |
| --- | --- |
| `Title`, `Author` | `title`, `author` (lookups never overwrite these) |
| `ISBN13`, else `ISBN` | `isbn_13`, `isbn_10` |
| `Publisher`, `Year Published` | `publisher`, `year` |
| `Exclusive Shelf` | `shelf` (`to-read`, `currently-reading`, `read` or a custom shelf) |
| `Bookshelves` | extra tags |
| `Book Id` | `goodreads_book_id`, written only when the book has no ISBN |

Every note gets the `book` tag. Description, cover and categories come from Open Library, then Google Books for whatever is still missing.

## Identity and re-runs

Notes are matched by `isbn_13`, then by `goodreads_book_id`. Re-running the import updates matching notes, renames them if the canonical filename changed, and always keeps the `## User Notes` section. Filenames follow `Title - Author (Publisher, Year).md`.
