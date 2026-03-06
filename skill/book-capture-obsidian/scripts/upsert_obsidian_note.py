#!/usr/bin/env python3
"""Idempotent Obsidian note upsert for resolved book metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_config import get_env_str
from common_isbn import isbn13_to_isbn10, normalize_isbn
from common_json import fail_and_print, make_result, print_json, read_json_file

STAGE = "upsert_obsidian_note"
BEGIN_MARKER = "<!-- BOOK_CAPTURE:BEGIN AUTO -->"
END_MARKER = "<!-- BOOK_CAPTURE:END AUTO -->"

VALID_STATUS = {"inbox", "to-read", "reading", "finished", "paused", "dropped", "dnf", "reference"}

MetadataDict = Dict[str, Any]


def _slugify_filename(value: str) -> str:
    value = (value or "Book").strip()
    value = re.sub(r"[\\/:*?\"<>|]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.rstrip(".")
    return value or "Book"


def _as_str_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _safe_float01(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if num < 0:
        return 0.0
    if num > 1:
        return 1.0
    return round(num, 4)


def _safe_rating(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num < 0 or num > 5:
        return None
    return round(num, 2)


def _parse_year_from_date(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(\d{4})", text)
    if not match:
        return None
    year = int(match.group(1))
    if year < 1000 or year > 3000:
        return None
    return year


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_list(values: List[str]) -> str:
    if not values:
        return "[]"
    lines = []
    for item in values:
        lines.append(f"  - {_yaml_scalar(item)}")
    return "\n".join(lines)


def _prepare_metadata(payload: MetadataDict) -> Tuple[Optional[str], Optional[MetadataDict], Optional[MetadataDict], Optional[str]]:
    """Accept envelope and raw metadata payload contracts."""
    if not isinstance(payload, dict):
        return None, None, None, "metadata payload must be a JSON object"

    if isinstance(payload.get("metadata"), dict):
        metadata = payload["metadata"]
    else:
        metadata = payload

    isbn_value = (
        payload.get("isbn13")
        or payload.get("isbn")
        or metadata.get("isbn13")
        or metadata.get("isbn")
    )

    isbn13 = normalize_isbn(str(isbn_value or ""))
    if not isbn13:
        return None, None, None, "metadata payload missing valid isbn/isbn13"

    title = str(metadata.get("title") or "").strip()
    if not title:
        return None, None, None, "metadata payload missing title"

    clean_metadata: MetadataDict = {
        "authors": _as_str_list(metadata.get("authors") or []),
        "categories": _as_str_list(metadata.get("categories") or []),
        "cover_image": str(metadata.get("cover_image") or "").strip() or None,
        "description": str(metadata.get("description") or "").strip() or None,
        "language": str(metadata.get("language") or "").strip() or None,
        "page_count": metadata.get("page_count"),
        "published_date": str(metadata.get("published_date") or "").strip() or None,
        "publisher": str(metadata.get("publisher") or "").strip() or None,
        "source": str(metadata.get("source") or payload.get("source") or "manual").strip() or "manual",
        "source_url": str(metadata.get("source_url") or "").strip() or None,
        "title": title,
    }

    try:
        if clean_metadata["page_count"] is not None:
            clean_metadata["page_count"] = int(clean_metadata["page_count"])
            if clean_metadata["page_count"] < 1:
                clean_metadata["page_count"] = None
    except Exception:
        clean_metadata["page_count"] = None

    status = str(payload.get("status") or "to-read").strip().lower()
    if status not in VALID_STATUS:
        status = "to-read"

    tags = _as_str_list(payload.get("tags") or [])
    for category in clean_metadata.get("categories") or []:
        if category not in tags:
            tags.append(category)

    extras: MetadataDict = {
        "status": status,
        "rating": _safe_rating(payload.get("rating")),
        "needs_review": bool(payload.get("needs_review", False)),
        "source_confidence": _safe_float01(payload.get("source_confidence", 0.0), default=0.0),
        "tags": tags,
        "started": str(payload.get("started") or "").strip() or None,
        "finished": str(payload.get("finished") or "").strip() or None,
    }

    return isbn13, clean_metadata, extras, None


def _render_auto_block(isbn13: str, metadata: MetadataDict, extras: MetadataDict) -> str:
    isbn10 = isbn13_to_isbn10(isbn13)
    authors = metadata.get("authors") or []
    published_year = _parse_year_from_date(metadata.get("published_date"))
    tags = extras.get("tags") or []

    frontmatter_lines = [
        "---",
        f"title: {_yaml_scalar(metadata['title'])}",
        "authors:",
        _yaml_list(authors),
        f"isbn_10: {_yaml_scalar(isbn10)}",
        f"isbn_13: {_yaml_scalar(isbn13)}",
        f"publisher: {_yaml_scalar(metadata.get('publisher'))}",
        f"published_year: {_yaml_scalar(published_year)}",
        f"status: {_yaml_scalar(extras.get('status'))}",
        f"rating: {_yaml_scalar(extras.get('rating'))}",
        f"started: {_yaml_scalar(extras.get('started'))}",
        f"finished: {_yaml_scalar(extras.get('finished'))}",
        f"source: {_yaml_scalar(metadata.get('source'))}",
        f"source_confidence: {_yaml_scalar(extras.get('source_confidence'))}",
        f"needs_review: {_yaml_scalar(extras.get('needs_review'))}",
        "tags:",
        _yaml_list(tags),
        f"cover_image: {_yaml_scalar(metadata.get('cover_image'))}",
        f"source_url: {_yaml_scalar(metadata.get('source_url'))}",
        "---",
    ]

    details_lines = [
        *frontmatter_lines,
        "",
        BEGIN_MARKER,
        f"# {metadata['title']}",
        "",
        "## Summary",
        metadata.get("description") or "",
        "",
        "## Metadata Audit",
        "- Canonical identifiers: see frontmatter fields `isbn_13` and `isbn_10`.",
        f"- Authors: {', '.join(authors) if authors else 'N/A'}",
        f"- Publisher: {metadata.get('publisher') or 'N/A'}",
        f"- Published: {metadata.get('published_date') or 'N/A'}",
        f"- Language: {metadata.get('language') or 'N/A'}",
        f"- Pages: {metadata.get('page_count') if metadata.get('page_count') is not None else 'N/A'}",
        f"- Metadata Source: {metadata.get('source') or 'N/A'}",
        END_MARKER,
    ]

    return "\n".join(details_lines)


def _split_by_markers(content: str) -> Tuple[bool, str, str]:
    begin_idx = content.find(BEGIN_MARKER)
    end_idx = content.find(END_MARKER)
    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return False, "", content

    end_after = end_idx + len(END_MARKER)
    prefix = content[:begin_idx]
    suffix = content[end_after:]
    return True, prefix, suffix


def _find_existing_note_by_isbn(vault_path: str, notes_dir: str, isbn13: str) -> Optional[Path]:
    root = Path(vault_path).expanduser() / Path(notes_dir)
    if not root.exists():
        return None
    pattern = f"*({isbn13}).md"
    matches = sorted(root.rglob(pattern))
    return matches[0] if matches else None


def _build_note_path(
    isbn13: str,
    metadata: MetadataDict,
    target_note: Optional[str],
    vault_path: str,
    notes_dir: str,
) -> Path:
    if target_note:
        return Path(target_note).expanduser()

    existing = _find_existing_note_by_isbn(vault_path=vault_path, notes_dir=notes_dir, isbn13=isbn13)
    if existing:
        return existing

    vault = Path(vault_path).expanduser()
    rel_dir = Path(notes_dir)
    title = _slugify_filename(str(metadata.get("title") or "Book"))
    filename = _slugify_filename(f"{title} ({isbn13})") + ".md"
    return vault / rel_dir / filename


def _upsert_note_core(payload: MetadataDict, vault_path: str, notes_dir: str, target_note: Optional[str]) -> dict:
    isbn13, metadata, extras, error = _prepare_metadata(payload)
    if error or not isbn13 or metadata is None or extras is None:
        return make_result(STAGE, ok=False, error=error or "invalid metadata payload", note_path=None)

    note_path = _build_note_path(
        isbn13=isbn13,
        metadata=metadata,
        target_note=target_note,
        vault_path=vault_path,
        notes_dir=notes_dir,
    )
    note_path.parent.mkdir(parents=True, exist_ok=True)

    auto_block = _render_auto_block(isbn13=isbn13, metadata=metadata, extras=extras)
    created = not note_path.exists()
    preserved_user_content = False

    if created:
        new_content = f"{auto_block}\n\n## User Notes\n\n"
    else:
        existing = note_path.read_text(encoding="utf-8")
        has_markers, _prefix, suffix = _split_by_markers(existing)
        if has_markers:
            # Keep user-owned content after END marker, regenerate managed block including frontmatter.
            new_content = f"{auto_block}{suffix}"
            preserved_user_content = True
        else:
            if existing.strip():
                new_content = f"{auto_block}\n\n{existing}"
                preserved_user_content = True
            else:
                new_content = f"{auto_block}\n\n## User Notes\n\n"

    existing_content = note_path.read_text(encoding="utf-8") if note_path.exists() else None
    updated = existing_content != new_content
    if updated:
        note_path.write_text(new_content, encoding="utf-8")

    return make_result(
        STAGE,
        ok=True,
        error=None,
        note_path=str(note_path),
        created=created,
        updated=updated,
        preserved_user_content=preserved_user_content,
        isbn13=isbn13,
        title=metadata["title"],
        status=extras.get("status"),
        needs_review=extras.get("needs_review"),
    )


def _resolve_upsert_args(*args: Any, **kwargs: Any) -> Tuple[Optional[MetadataDict], str, str, Optional[str], Optional[str]]:
    """Support both canonical and legacy/test call patterns."""
    payload = kwargs.get("payload") or kwargs.get("book")
    target_note = kwargs.get("target_note") or kwargs.get("note_path") or kwargs.get("path") or kwargs.get("file_path")
    vault_path = kwargs.get("vault_path") or get_env_str("BOOK_CAPTURE_VAULT_PATH", ".")
    notes_dir = kwargs.get("notes_dir") or get_env_str("BOOK_CAPTURE_NOTES_DIR", "Books")

    if len(args) == 4 and isinstance(args[0], dict):
        payload = args[0]
        vault_path = str(args[1])
        notes_dir = str(args[2])
        target_note = str(args[3]) if args[3] else None
    elif len(args) == 3 and isinstance(args[0], dict):
        payload = args[0]
        vault_path = str(args[1])
        notes_dir = str(args[2])
    elif len(args) >= 2:
        a0, a1 = args[0], args[1]
        if isinstance(a0, (str, Path)) and isinstance(a1, dict):
            target_note = str(a0)
            payload = a1
        elif isinstance(a0, dict) and isinstance(a1, (str, Path)):
            payload = a0
            target_note = str(a1)
    elif len(args) == 1:
        if isinstance(args[0], dict):
            payload = args[0]
        elif isinstance(args[0], (str, Path)):
            target_note = str(args[0])

    if payload is None:
        return None, str(vault_path), str(notes_dir), str(target_note) if target_note else None, "missing payload/book argument"

    if not isinstance(payload, dict):
        return None, str(vault_path), str(notes_dir), str(target_note) if target_note else None, "payload/book must be a JSON object"

    return payload, str(vault_path), str(notes_dir), str(target_note) if target_note else None, None


def upsert_note(*args: Any, **kwargs: Any) -> dict:
    """Public upsert entrypoint.

    Canonical call:
      upsert_note(payload=<dict>, vault_path=<str>, notes_dir=<str>, target_note=<str|None>)

    Also accepts legacy/test patterns such as:
      upsert_note(note_path, payload)
      upsert_note(payload, note_path)
      upsert_note(note_path=<path>, book=<dict>)
    """
    payload, vault_path, notes_dir, target_note, error = _resolve_upsert_args(*args, **kwargs)
    if error or payload is None:
        return make_result(STAGE, ok=False, error=error or "invalid arguments", note_path=None)
    return _upsert_note_core(payload=payload, vault_path=vault_path, notes_dir=notes_dir, target_note=target_note)


def _self_check() -> dict:
    payload = {
        "isbn13": "9780201633610",
        "metadata": {
            "title": "Design Patterns",
            "authors": ["Gamma", "Helm", "Johnson", "Vlissides"],
            "source": "self_check",
        },
        "status": "reading",
        "source_confidence": 0.92,
        "tags": ["software", "patterns"],
    }
    isbn13, metadata, extras, error = _prepare_metadata(payload)
    ok = bool(isbn13 and metadata and extras and not error)
    return make_result(
        STAGE,
        ok=ok,
        error=error,
        checks={
            "prepared_isbn13": isbn13,
            "prepared_title": metadata.get("title") if metadata else None,
            "prepared_status": extras.get("status") if extras else None,
        },
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-json", help="Path to metadata JSON (resolve_metadata output)")
    parser.add_argument("--vault-path", default=get_env_str("BOOK_CAPTURE_VAULT_PATH", "."), help="Obsidian vault root")
    parser.add_argument("--notes-dir", default=get_env_str("BOOK_CAPTURE_NOTES_DIR", "Books"), help="Notes directory inside vault")
    parser.add_argument("--target-note", default=get_env_str("BOOK_CAPTURE_TARGET_NOTE", ""), help="Optional explicit note path")
    parser.add_argument("--self-check", action="store_true", help="Run internal quick checks")
    args = parser.parse_args(argv)

    if args.self_check:
        result = _self_check()
        print_json(result)
        return 0 if result.get("ok") else 1

    if not args.metadata_json:
        return fail_and_print(STAGE, "--metadata-json is required", note_path=None)

    try:
        payload = read_json_file(args.metadata_json)
    except Exception as exc:
        return fail_and_print(STAGE, f"failed to read metadata JSON: {exc}", note_path=None)

    result = upsert_note(
        payload=payload,
        vault_path=args.vault_path,
        notes_dir=args.notes_dir,
        target_note=args.target_note or None,
    )
    print_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
