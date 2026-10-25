# Changelog

## 1.3.0 (unreleased)

- Quota-aware metadata: Open Library first, Google Books only for missing fields, SQLite cache, per-run Google budget and a persisted cooldown after HTTP 429. Goodreads dry runs make no network calls; `--limit` for small batches.
- Goodreads rows without an ISBN are imported (previously all skipped) and matched on re-runs by `goodreads_book_id`.
- Dashboard counts by `shelf`, uses the configured notes folder, finds its template from any working directory, and cannot write outside the vault.
- Scripts refuse to write without an existing vault directory.
- `--group-by-shelf` keeps notes inside the vault and never deletes a note on a name collision.
- Related-note folders and note language (`en`/`pt`) are configurable; no vault-specific folder names.
- Bulk imports cache parsed notes (600 rows: 16 s to 2.6 s).
- SKILL.md rewritten with OpenClaw requirements metadata, network disclosure and `setup.sh`; dependencies pinned and audited; developer scripts no longer shipped inside the skill.

## 1.2.1

- Photo import: semantic tags, related links, `Title - Author (Publisher, Year)` filenames, simplified frontmatter.
