# Data Contracts

All scripts return deterministic JSON envelopes:

```json
{
  "stage": "string",
  "ok": true,
  "error": null
}
```

Additional fields vary per stage.

## 1) ISBN Extraction Output (`extract_isbn.py`)

```json
{
  "stage": "extract_isbn",
  "ok": true,
  "error": null,
  "source_image": "...",
  "method": "barcode|ocr",
  "isbn13": "978...",
  "isbn_candidates": ["978..."],
  "warnings": []
}
```

## 2) Metadata Resolution Output (`resolve_metadata.py`)

```json
{
  "stage": "resolve_metadata",
  "ok": true,
  "error": null,
  "isbn13": "978...",
  "metadata": {
    "title": "...",
    "authors": ["..."],
    "publisher": "...",
    "published_date": "...",
    "description": "...",
    "page_count": 123,
    "language": "en",
    "categories": ["..."],
    "cover_image": "...",
    "source": "google_books|openlibrary",
    "source_url": "..."
  },
  "warnings": []
}
```

## 3) Upsert Input Contract (`upsert_obsidian_note.py`)

```json
{
  "isbn13": "978...",
  "status": "to-read|reading|finished|paused|dropped|dnf|reference|inbox",
  "rating": 4.0,
  "needs_review": false,
  "source_confidence": 0.95,
  "started": null,
  "finished": "YYYY-MM-DD",
  "tags": ["book", "science"],
  "metadata": {
    "title": "...",
    "authors": ["..."],
    "publisher": "...",
    "published_date": "...",
    "description": "...",
    "page_count": 123,
    "language": "en",
    "categories": ["..."],
    "cover_image": "...",
    "source": "photo|goodreads_csv|manual",
    "source_url": "..."
  }
}
```

## 4) Upsert Output Contract

```json
{
  "stage": "upsert_obsidian_note",
  "ok": true,
  "error": null,
  "note_path": "...",
  "created": true,
  "updated": true,
  "preserved_user_content": false,
  "isbn13": "978...",
  "title": "...",
  "status": "to-read",
  "needs_review": false
}
```

## 5) Photo Ingest Output (`ingest_photo.py`)

```json
{
  "stage": "ingest_photo",
  "ok": true,
  "error": null,
  "image_path": "...",
  "isbn13": "978...",
  "note_path": "...",
  "extract": {"...": "..."},
  "metadata": {"...": "..."},
  "upsert": {"...": "..."},
  "warnings": []
}
```

## 6) Migration Output (`migrate_goodreads_csv.py`)

```json
{
  "stage": "migrate_goodreads_csv",
  "ok": true,
  "error": null,
  "csv_path": "...",
  "dry_run": true,
  "stats": {
    "created": 0,
    "updated": 0,
    "unchanged": 0,
    "skipped": 0,
    "total_processed": 0
  },
  "errors": []
}
```

## Safety Rules

- Never include credentials, tokens, or personal identifiers in any contract.
- Keep output deterministic (stable keys and value types) to simplify automation.
