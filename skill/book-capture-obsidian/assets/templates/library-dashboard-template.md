# Library Dashboard

## Overview

- Total books: `{{total_books}}`
- To read: `{{to_read_count}}`
- Reading: `{{reading_count}}`
- Finished: `{{finished_count}}`
- Needs review: `{{needs_review_count}}`

## Recently Added

```dataview
TABLE authors, status, rating
FROM "Books"
SORT file.ctime DESC
LIMIT 20
```

## Currently Reading

```dataview
TABLE authors, rating
FROM "Books"
WHERE status = "reading"
SORT file.mtime DESC
```

## Needs Review

```dataview
TABLE authors, source_confidence
FROM "Books"
WHERE needs_review = true
SORT source_confidence ASC
```
