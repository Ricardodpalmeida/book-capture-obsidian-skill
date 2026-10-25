# Troubleshooting

## No ISBN extracted from a photo

`extract_isbn.py` returns `ok=false` with `no valid ISBN found`.

- Check the barcode is sharp and fills a good part of the frame; a photo of the back cover works best.
- Run `PY {baseDir}/scripts/extract_isbn.py --diagnose-deps` to see which of `zbarimg`, `pyzbar`, `pytesseract` and `tesseract` are available. Install `zbar-tools` (Debian/Ubuntu) or `zbar` (Homebrew) for barcodes, `tesseract-ocr` for OCR.
- If OCR times out, raise `BOOK_CAPTURE_TESSERACT_TIMEOUT_SECONDS`.
- Otherwise ask the user for the ISBN or title and use `resolve_metadata.py`.

## Metadata not found, or notes without a description

- `warnings` lists each provider's answer. `openlibrary returned no entry` and `google books returned no items` are real misses; try a title lookup.
- `google_books skipped: cooling down after a rate limit` or `per-run request budget reached` means the quota guard stopped Google. The note was written with Open Library data. Re-run later, or set `BOOK_CAPTURE_GOOGLE_API_KEY`.
- `found no close title/author match` means a title search returned only other books (sequels, translations listed under another script, same title by a different author). Nothing was guessed. Ask the user for the ISBN, which is always more reliable than a title.
- A wrong cached answer can be cleared by deleting `metadata.sqlite3` in the cache folder (see `configuration.md`).
- HTTP 400 or 403 from Google usually means an invalid or restricted API key.

## A note did not update

- Check `created`, `updated` and `note_path` in the JSON.
- Notes are matched by `isbn_13`, then `goodreads_book_id`. A note created by hand without either field is not matched; add `isbn_13` to its frontmatter.
- Everything above `## User Notes` is regenerated on each run; write personal notes below that heading.

## The dashboard shows zero books

- `--notes-dir` (or `BOOK_CAPTURE_NOTES_DIR`) must point at the folder that holds the notes.
- Status counts come from the `shelf` property. Custom shelf names can be mapped with `BOOK_CAPTURE_SHELVES_TO_READ`, `BOOK_CAPTURE_SHELVES_READING` and `BOOK_CAPTURE_SHELVES_READ`.
- The tables need the Dataview community plugin in Obsidian.

## The Goodreads import skips rows

`errors` names the line and reason. A row without a title is always skipped. Encoding errors usually mean the file was re-saved in another program; export again from Goodreads.
