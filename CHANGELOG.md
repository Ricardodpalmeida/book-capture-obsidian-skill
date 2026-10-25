# Changelog

## 1.3.2

- Security: titles and summaries from external sources can no longer inject code blocks or Dataview JS queries into book notes. Backticks and tildes in that text are escaped. Existing notes are rewritten safely on the next run.

## 1.3.1

- Sharper description and README, plus links to the author's other skills and site. No code changes.

## 1.3.0 (unreleased)

- Quota-aware metadata: Open Library first, Google Books only for missing fields, SQLite cache, per-run Google budget and a persisted cooldown after HTTP 429. Goodreads dry runs make no network calls; `--limit` for small batches.
- Open Library ISBN lookups now return a description: the `jscmd=data` response has no work link, so the resolver follows the edition record to the work. Before this, almost every ISBN fell through to Google Books for the description, which is what exhausted the free quota.
- Title searches (Open Library and Google Books) only accept a result whose title and author match the query, and never adopt an edition ISBN. Checked against live Open Library data, where "The Three-Body Problem" by Liu Cixin otherwise resolves to its sequel or to an unrelated physics book.
- When an ISBN has no Open Library record (common for Portuguese and other non-English editions), the resolver tries the Open Library title and author search before Google. Work-level search results no longer set a publisher, because the list belongs to other editions.
- Descriptions with Windows line endings no longer make every re-run rewrite the note.
- Goodreads rows without an ISBN are imported (previously all skipped) and matched on re-runs by `goodreads_book_id`.
- Dashboard counts by `shelf`, uses the configured notes folder, finds its template from any working directory, and cannot write outside the vault.
- Scripts refuse to write without an existing vault directory.
- `--group-by-shelf` keeps notes inside the vault and never deletes a note on a name collision.
- Related-note folders and note language (`en`/`pt`) are configurable; no vault-specific folder names.
- Bulk imports cache parsed notes (600 rows: 16 s to 2.6 s).
- SKILL.md rewritten with OpenClaw requirements metadata, network disclosure and `setup.sh`; dependencies pinned and audited; developer scripts no longer shipped inside the skill.

## 1.2.1

- Photo import: semantic tags, related links, `Title - Author (Publisher, Year)` filenames, simplified frontmatter.
