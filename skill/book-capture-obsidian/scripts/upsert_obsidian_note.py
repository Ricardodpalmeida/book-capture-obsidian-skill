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
    return "\n".join(f"  - {_yaml_scalar(item)}" for item in values)


def _safe_http_url(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return None


def _series_info_from_title(title: str) -> Tuple[Optional[str], Optional[str]]:
    # Ex: "Leviathan Wakes (The Expanse, #1)"
    m = re.search(r"\(([^\)#]+),\s*#([0-9]+)\)", title)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()


def _prepare_metadata(payload: MetadataDict) -> Tuple[Optional[str], Optional[str], Optional[MetadataDict], Optional[MetadataDict], Optional[str]]:
    """Accept envelope and raw metadata payload contracts."""
    if not isinstance(payload, dict):
        return None, None, None, None, "metadata payload must be a JSON object"

    if isinstance(payload.get("metadata"), dict):
        metadata = payload["metadata"]
    else:
        metadata = payload

    title = str(metadata.get("title") or "").strip()
    if not title:
        return None, None, None, None, "metadata payload missing title"

    isbn_value = (
        payload.get("isbn13")
        or payload.get("isbn")
        or metadata.get("isbn13")
        or metadata.get("isbn")
    )
    isbn13 = normalize_isbn(str(isbn_value or ""))

    goodreads = payload.get("goodreads") if isinstance(payload.get("goodreads"), dict) else {}
    goodreads_book_id = str(
        payload.get("goodreads_book_id")
        or payload.get("book_id")
        or goodreads.get("book_id")
        or ""
    ).strip() or None

    if not isbn13 and not goodreads_book_id:
        return None, None, None, None, "metadata payload missing valid isbn and goodreads_book_id"

    clean_metadata: MetadataDict = {
        "authors": _as_str_list(metadata.get("authors") or []),
        "categories": _as_str_list(metadata.get("categories") or []),
        "cover_image": _safe_http_url(metadata.get("cover_image")),
        "description": str(metadata.get("description") or "").strip() or None,
        "language": str(metadata.get("language") or "").strip() or None,
        "page_count": metadata.get("page_count"),
        "published_date": str(metadata.get("published_date") or "").strip() or None,
        "publisher": str(metadata.get("publisher") or "").strip() or None,
        "source": str(metadata.get("source") or payload.get("source") or "manual").strip() or "manual",
        "source_url": _safe_http_url(metadata.get("source_url")),
        "title": title,
    }

    # Only keep cover image when it came from API metadata
    if clean_metadata.get("source") not in {"google_books", "openlibrary"}:
        clean_metadata["cover_image"] = None

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

    shelf = str(payload.get("shelf") or goodreads.get("exclusive_shelf") or status).strip().lower() or status

    tags = _as_str_list(payload.get("tags") or [])
    for category in clean_metadata.get("categories") or []:
        if category not in tags:
            tags.append(category)
    if "book" not in tags:
        tags.insert(0, "book")

    series_name, series_index = _series_info_from_title(title)
    if series_name:
        series_tag = f"series-{_slugify_filename(series_name).lower().replace(' ', '-') }"
        if series_tag not in tags:
            tags.append(series_tag)

    extras: MetadataDict = {
        "status": status,
        "shelf": shelf,
        "needs_review": bool(payload.get("needs_review", False)),
        "tags": tags,
        "started": str(payload.get("started") or "").strip() or None,
        "finished": str(payload.get("finished") or "").strip() or None,
        "series_name": series_name,
        "series_index": series_index,
    }

    return isbn13, goodreads_book_id, clean_metadata, extras, None


def _render_managed_block(isbn13: Optional[str], goodreads_book_id: Optional[str], metadata: MetadataDict, extras: MetadataDict) -> str:
    isbn10 = isbn13_to_isbn10(isbn13) if isbn13 else None
    authors = metadata.get("authors") or []
    published_year = _parse_year_from_date(metadata.get("published_date"))
    tags = extras.get("tags") or []
    summary = metadata.get("description")
    if not summary:
        author_text = ", ".join(authors) if authors else "Unknown author"
        publisher_text = metadata.get("publisher") or "Unknown publisher"
        year_text = str(published_year) if published_year else "unknown year"
        summary = f"Obra de {author_text}, publicada por {publisher_text} ({year_text})."

    frontmatter_lines = [
        "---",
        f"title: {_yaml_scalar(metadata['title'])}",
        "authors:",
        _yaml_list(authors),
        f"publisher: {_yaml_scalar(metadata.get('publisher'))}",
        f"published_date: {_yaml_scalar(metadata.get('published_date'))}",
        f"published_year: {_yaml_scalar(published_year)}",
        f"isbn_10: {_yaml_scalar(isbn10)}",
        f"isbn_13: {_yaml_scalar(isbn13)}",
        f"goodreads_book_id: {_yaml_scalar(goodreads_book_id)}",
        f"shelf: {_yaml_scalar(extras.get('shelf'))}",
        f"status: {_yaml_scalar(extras.get('status'))}",
        f"started: {_yaml_scalar(extras.get('started'))}",
        f"finished: {_yaml_scalar(extras.get('finished'))}",
        f"source: {_yaml_scalar(metadata.get('source'))}",
        f"source_url: {_yaml_scalar(metadata.get('source_url'))}",
        f"cover: {_yaml_scalar(metadata.get('cover_image'))}",
        f"needs_review: {_yaml_scalar(extras.get('needs_review'))}",
        "tags:",
        _yaml_list(tags),
    ]

    if extras.get("series_name"):
        frontmatter_lines.append(f"series: {_yaml_scalar(extras.get('series_name'))}")
        frontmatter_lines.append(f"series_index: {_yaml_scalar(extras.get('series_index'))}")

    frontmatter_lines.append("---")

    body_lines = [
        *frontmatter_lines,
        "",
        f"# {metadata['title']}",
        "",
        "## Sinopse",
        summary,
    ]

    if extras.get("series_name"):
        body_lines.extend(
            [
                "",
                "## Collection",
                f"- Series: [[Series - {extras['series_name']}]]",
                f"- Volume: {extras.get('series_index') or 'N/A'}",
            ]
        )

    return "\n".join(body_lines).strip() + "\n"


def _split_by_markers(content: str) -> Tuple[bool, str, str]:
    begin_idx = content.find(BEGIN_MARKER)
    end_idx = content.find(END_MARKER)
    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return False, "", content

    end_after = end_idx + len(END_MARKER)
    prefix = content[:begin_idx]
    suffix = content[end_after:]
    return True, prefix, suffix


def _extract_user_notes(existing: str) -> str:
    marker = "## User Notes"
    idx = existing.find(marker)
    if idx != -1:
        return existing[idx:].strip() + "\n"

    has_markers, _prefix, suffix = _split_by_markers(existing)
    if has_markers and suffix.strip():
        s = suffix.strip()
        if not s.startswith("## User Notes"):
            return "## User Notes\n\n" + s + "\n"
        return s + "\n"

    if existing.strip():
        return "## User Notes\n\n" + existing.strip() + "\n"

    return "## User Notes\n"


def _frontmatter_lookup(path: Path, key: str) -> Optional[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    if not lines:
        return None
    start = None
    for i, line in enumerate(lines[:20]):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        return None

    for line in lines[start + 1 : start + 80]:
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def _find_existing_note(vault_path: str, notes_dir: str, isbn13: Optional[str], goodreads_book_id: Optional[str]) -> Optional[Path]:
    root = Path(vault_path).expanduser() / Path(notes_dir)
    if not root.exists():
        return None

    # Fast path for legacy filenames with ISBN suffix
    if isbn13:
        matches = sorted(root.rglob(f"*({isbn13}).md"))
        if matches:
            return matches[0]

    # Frontmatter lookup fallback
    for note_path in root.rglob("*.md"):
        if isbn13:
            val = _frontmatter_lookup(note_path, "isbn_13")
            if val == isbn13:
                return note_path
        if goodreads_book_id:
            val = _frontmatter_lookup(note_path, "goodreads_book_id")
            if val == goodreads_book_id:
                return note_path

    return None


def _candidate_filename(metadata: MetadataDict) -> str:
    title = _slugify_filename(str(metadata.get("title") or "Book"))
    author = _slugify_filename((metadata.get("authors") or ["Unknown Author"])[0])
    publisher = _slugify_filename(str(metadata.get("publisher") or ""))
    year = _parse_year_from_date(metadata.get("published_date"))

    parts = [title, author]
    if publisher:
        parts.append(publisher)
    if year:
        parts.append(str(year))

    return _slugify_filename(" - ".join(parts)) + ".md"


def _build_note_path(
    isbn13: Optional[str],
    goodreads_book_id: Optional[str],
    metadata: MetadataDict,
    target_note: Optional[str],
    vault_path: str,
    notes_dir: str,
) -> Path:
    if target_note:
        return Path(target_note).expanduser()

    existing = _find_existing_note(vault_path=vault_path, notes_dir=notes_dir, isbn13=isbn13, goodreads_book_id=goodreads_book_id)
    if existing:
        return existing

    vault = Path(vault_path).expanduser()
    rel_dir = Path(notes_dir)
    base = _candidate_filename(metadata)
    path = vault / rel_dir / base

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    idx = 2
    while True:
        candidate = path.with_name(f"{stem} ({idx}){suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def _is_within_vault(note_path: Path, vault_path: str) -> bool:
    vault_root = Path(vault_path).expanduser().resolve()
    note_abs = note_path.expanduser().resolve()
    return note_abs == vault_root or vault_root in note_abs.parents


def _upsert_note_core(payload: MetadataDict, vault_path: str, notes_dir: str, target_note: Optional[str]) -> dict:
    isbn13, goodreads_book_id, metadata, extras, error = _prepare_metadata(payload)
    if error or metadata is None or extras is None:
        return make_result(STAGE, ok=False, error=error or "invalid metadata payload", note_path=None)

    note_path = _build_note_path(
        isbn13=isbn13,
        goodreads_book_id=goodreads_book_id,
        metadata=metadata,
        target_note=target_note,
        vault_path=vault_path,
        notes_dir=notes_dir,
    )

    if not _is_within_vault(note_path, vault_path=vault_path):
        return make_result(
            STAGE,
            ok=False,
            error=f"target note path escapes vault root: {note_path}",
            note_path=str(note_path),
        )

    note_path = note_path.expanduser().resolve()
    note_path.parent.mkdir(parents=True, exist_ok=True)

    managed = _render_managed_block(isbn13=isbn13, goodreads_book_id=goodreads_book_id, metadata=metadata, extras=extras)
    created = not note_path.exists()
    preserved_user_content = False

    if created:
        user_notes = "## User Notes\n"
    else:
        existing = note_path.read_text(encoding="utf-8")
        user_notes = _extract_user_notes(existing)
        preserved_user_content = bool(user_notes.strip())

    new_content = managed.rstrip() + "\n\n" + user_notes.strip() + "\n"

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
        goodreads_book_id=goodreads_book_id,
        title=metadata["title"],
        status=extras.get("status"),
        shelf=extras.get("shelf"),
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
        "shelf": "sci-com",
        "metadata": {
            "title": "Design Patterns",
            "authors": ["Gamma", "Helm", "Johnson", "Vlissides"],
            "publisher": "Addison-Wesley",
            "published_date": "1994",
            "source": "self_check",
        },
        "status": "reading",
        "tags": ["software", "patterns"],
    }
    isbn13, goodreads_book_id, metadata, extras, error = _prepare_metadata(payload)
    ok = bool((isbn13 or goodreads_book_id) and metadata and extras and not error)
    return make_result(
        STAGE,
        ok=ok,
        error=error,
        checks={
            "prepared_isbn13": isbn13,
            "prepared_title": metadata.get("title") if metadata else None,
            "prepared_status": extras.get("status") if extras else None,
            "prepared_shelf": extras.get("shelf") if extras else None,
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
