#!/usr/bin/env python3
"""Migrate Goodreads CSV exports into Obsidian notes with deterministic upsert."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_config import get_env_str
from common_isbn import normalize_isbn
from common_json import fail_and_print, make_result, print_json
from upsert_obsidian_note import upsert_note

STAGE = "migrate_goodreads_csv"


def _normalize_header_map(row: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key in row.keys():
        out[key.strip().lower()] = key
    return out


def _get_value(row: Dict[str, Any], header_map: Dict[str, str], name: str) -> str:
    key = header_map.get(name.lower())
    if key is None:
        return ""
    return str(row.get(key, "") or "").strip()


def _split_tags(value: str) -> List[str]:
    if not value:
        return []
    out: List[str] = []
    seen = set()
    for raw in value.split(","):
        tag = raw.strip()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def _map_status(exclusive_shelf: str) -> str:
    shelf = exclusive_shelf.strip().lower()
    if shelf in {"to-read", "to read", "want-to-read"}:
        return "to-read"
    if shelf in {"currently-reading", "currently reading", "reading"}:
        return "reading"
    if shelf in {"read", "finished"}:
        return "finished"
    if shelf in {"did-not-finish", "dnf"}:
        return "dnf"
    return "inbox"


def _parse_rating(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        rating = float(value)
    except ValueError:
        return None
    if rating < 0 or rating > 5:
        return None
    return rating


def _pick_isbn13(isbn13_raw: str, isbn10_raw: str) -> Optional[str]:
    normalized_13 = normalize_isbn(isbn13_raw or "")
    if normalized_13:
        return normalized_13
    normalized_10 = normalize_isbn(isbn10_raw or "")
    if normalized_10:
        return normalized_10
    return None


def _build_payload(row: Dict[str, Any], header_map: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    title = _get_value(row, header_map, "Title")
    author = _get_value(row, header_map, "Author")
    isbn10_raw = _get_value(row, header_map, "ISBN")
    isbn13_raw = _get_value(row, header_map, "ISBN13")
    shelf = _get_value(row, header_map, "Exclusive Shelf")
    bookshelves = _get_value(row, header_map, "Bookshelves")
    my_rating = _get_value(row, header_map, "My Rating")
    date_read = _get_value(row, header_map, "Date Read")
    date_added = _get_value(row, header_map, "Date Added")
    book_id = _get_value(row, header_map, "Book Id")

    if not title:
        return None, "missing title"

    isbn13 = _pick_isbn13(isbn13_raw=isbn13_raw, isbn10_raw=isbn10_raw)
    if not isbn13:
        return None, "missing valid ISBN"

    tags = _split_tags(bookshelves)
    status = _map_status(shelf)
    rating = _parse_rating(my_rating)

    payload: Dict[str, Any] = {
        "isbn13": isbn13,
        "status": status,
        "rating": rating,
        "needs_review": False,
        "source_confidence": 0.95,
        "started": None,
        "finished": date_read or None,
        "tags": tags,
        "metadata": {
            "title": title,
            "authors": [author] if author else [],
            "categories": tags,
            "description": None,
            "publisher": None,
            "published_date": None,
            "page_count": None,
            "language": None,
            "cover_image": None,
            "source": "goodreads_csv",
            "source_url": None,
        },
        "goodreads": {
            "book_id": book_id or None,
            "date_added": date_added or None,
            "exclusive_shelf": shelf or None,
        },
    }
    return payload, None


def migrate_csv(csv_path: str, vault_path: str, notes_dir: str, dry_run: bool = True) -> Dict[str, Any]:
    path = Path(csv_path).expanduser()
    if not path.exists():
        return make_result(STAGE, ok=False, error=f"csv file not found: {path}")

    created = 0
    updated = 0
    unchanged = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return make_result(STAGE, ok=False, error="csv has no header")

        header_map = _normalize_header_map({name: name for name in reader.fieldnames})

        for idx, row in enumerate(reader, start=2):
            payload, err = _build_payload(row=row, header_map=header_map)
            if err or payload is None:
                skipped += 1
                errors.append({"line": idx, "error": err or "invalid row"})
                continue

            if dry_run:
                continue

            result = upsert_note(payload=payload, vault_path=vault_path, notes_dir=notes_dir, target_note=None)
            if not result.get("ok"):
                skipped += 1
                errors.append({"line": idx, "error": result.get("error") or "upsert failed"})
                continue

            if result.get("created"):
                created += 1
            elif result.get("updated"):
                updated += 1
            else:
                unchanged += 1

    total_processed = created + updated + unchanged + skipped

    return make_result(
        STAGE,
        ok=True,
        error=None,
        csv_path=str(path),
        dry_run=dry_run,
        stats={
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "skipped": skipped,
            "total_processed": total_processed,
        },
        errors=errors[:200],
    )


def _self_check() -> Dict[str, Any]:
    sample_payload, err = _build_payload(
        row={
            "Title": "Sample Book",
            "Author": "Sample Author",
            "ISBN": "0306406152",
            "ISBN13": "",
            "Exclusive Shelf": "read",
            "Bookshelves": "non-fiction,science",
            "My Rating": "4",
            "Date Read": "2025/01/01",
            "Date Added": "2024/01/01",
            "Book Id": "123",
        },
        header_map={
            "title": "Title",
            "author": "Author",
            "isbn": "ISBN",
            "isbn13": "ISBN13",
            "exclusive shelf": "Exclusive Shelf",
            "bookshelves": "Bookshelves",
            "my rating": "My Rating",
            "date read": "Date Read",
            "date added": "Date Added",
            "book id": "Book Id",
        },
    )

    ok = sample_payload is not None and err is None and sample_payload.get("isbn13") == "9780306406157"
    return make_result(
        STAGE,
        ok=ok,
        error=err,
        checks={
            "isbn13": sample_payload.get("isbn13") if sample_payload else None,
            "status": sample_payload.get("status") if sample_payload else None,
        },
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", help="Path to Goodreads CSV export")
    parser.add_argument("--vault-path", default=get_env_str("BOOK_CAPTURE_VAULT_PATH", "."), help="Obsidian vault root")
    parser.add_argument("--notes-dir", default=get_env_str("BOOK_CAPTURE_NOTES_DIR", "Books"), help="Notes directory inside vault")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing notes")
    parser.add_argument("--self-check", action="store_true", help="Run internal quick checks")
    args = parser.parse_args(argv)

    if args.self_check:
        result = _self_check()
        print_json(result)
        return 0 if result.get("ok") else 1

    if not args.csv:
        return fail_and_print(STAGE, "--csv is required")

    result = migrate_csv(csv_path=args.csv, vault_path=args.vault_path, notes_dir=args.notes_dir, dry_run=args.dry_run)
    print_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
