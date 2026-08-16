from __future__ import annotations

from pathlib import Path

from upsert_obsidian_note import upsert_note


def _payload(title: str = "The Testing Book") -> dict:
    return {
        "isbn13": "9780306406157",
        "shelf": "sci-com",
        "tags": ["book", "testing"],
        "metadata": {
            "title": title,
            "authors": ["Test Author"],
            "publisher": "Test Press",
            "published_date": "2024-03-01",
            "description": "A useful test description.",
            "page_count": 321,
            "language": "en",
            "categories": ["Software Testing"],
            "cover_image": "https://example.invalid/cover.jpg",
            "source": "unit_test",
            "source_url": "https://example.invalid/book",
        },
    }


def test_upsert_is_idempotent_and_writes_rich_note_only_in_tmp_path(tmp_path: Path):
    note_path = tmp_path / "Books" / "explicit.md"
    first = upsert_note(
        payload=_payload(),
        vault_path=str(tmp_path),
        notes_dir="Books",
        target_note=str(note_path),
    )
    first_content = note_path.read_text(encoding="utf-8")
    second = upsert_note(
        payload=_payload(),
        vault_path=str(tmp_path),
        notes_dir="Books",
        target_note=str(note_path),
    )

    assert first["ok"] is True and first["created"] is True
    assert second["ok"] is True and second["updated"] is False
    assert note_path.read_text(encoding="utf-8") == first_content
    assert "isbn_13: \"9780306406157\"" in first_content
    assert "## Sinopse" in first_content
    assert '  - "software-testing"' in first_content


def test_upsert_preserves_user_notes_when_managed_metadata_changes(tmp_path: Path):
    note_path = tmp_path / "Books" / "explicit.md"
    upsert_note(_payload(), str(tmp_path), "Books", str(note_path))
    content = note_path.read_text(encoding="utf-8")
    note_path.write_text(content + "\nMy handwritten observation.\n", encoding="utf-8")

    updated = upsert_note(_payload("The Testing Book, Revised"), str(tmp_path), "Books", str(note_path))
    new_content = note_path.read_text(encoding="utf-8")

    assert updated["ok"] is True
    assert updated["preserved_user_content"] is True
    assert "My handwritten observation." in new_content
    assert "The Testing Book, Revised" in new_content


def test_upsert_rejects_explicit_target_outside_vault(tmp_path: Path):
    vault = tmp_path / "vault"
    outside = tmp_path / "outside.md"
    result = upsert_note(_payload(), str(vault), "Books", str(outside))
    assert result["ok"] is False
    assert not outside.exists()
