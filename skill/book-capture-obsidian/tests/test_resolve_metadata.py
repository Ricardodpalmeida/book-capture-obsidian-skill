from __future__ import annotations

import resolve_metadata

ISBN = "9780306406157"


def test_google_failure_falls_back_to_openlibrary(monkeypatch):
    expected = {
        "title": "Fallback Book",
        "authors": ["Fallback Author"],
        "publisher": None,
        "published_date": None,
        "description": None,
        "page_count": None,
        "language": None,
        "categories": [],
        "cover_image": None,
        "source": "openlibrary",
        "source_url": None,
    }
    monkeypatch.setenv("BOOK_CAPTURE_METADATA_PROVIDER_ORDER", "google_books,openlibrary")
    monkeypatch.setattr(
        resolve_metadata,
        "_from_google_books",
        lambda **_kwargs: (None, "google books rate limit (429)"),
    )
    monkeypatch.setattr(resolve_metadata, "_from_openlibrary", lambda **_kwargs: (expected, None))

    result = resolve_metadata.resolve_book_metadata(ISBN)

    assert result["ok"] is True
    assert result["metadata"] == expected
    assert result["warnings"] == ["google books rate limit (429)"]


def test_all_provider_failures_return_backward_compatible_envelope(monkeypatch):
    monkeypatch.setenv("BOOK_CAPTURE_METADATA_PROVIDER_ORDER", "google_books,openlibrary")
    monkeypatch.setattr(resolve_metadata, "_from_google_books", lambda **_kwargs: (None, "google failed"))
    monkeypatch.setattr(resolve_metadata, "_from_openlibrary", lambda **_kwargs: (None, "open failed"))

    result = resolve_metadata.resolve_book_metadata(ISBN)

    assert result == {
        "stage": "resolve_metadata",
        "ok": False,
        "error": "metadata not found in configured providers",
        "isbn13": ISBN,
        "metadata": None,
        "warnings": ["google failed", "open failed"],
    }
