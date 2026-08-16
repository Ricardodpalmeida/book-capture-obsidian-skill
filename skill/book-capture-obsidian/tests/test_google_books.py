from __future__ import annotations

import json
from typing import Any

import pytest

import google_books
import migrate_goodreads_csv
import resolve_metadata

ISBN = "9780306406157"
OTHER_ISBN = "9780201633610"
SENTINEL = "test-key-marker-never-leak"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _payload(isbn: str = ISBN, **volume_overrides: Any) -> dict:
    volume = {
        "title": "Test Book",
        "authors": ["Test Author"],
        "publisher": "Test Press",
        "publishedDate": "2024",
        "description": "Description",
        "pageCount": 200,
        "language": "en",
        "categories": ["Testing"],
        "imageLinks": {"thumbnail": "http://books.google.test/cover?zoom=1"},
        "infoLink": "https://books.google.test/info",
        "industryIdentifiers": [{"type": "ISBN_13", "identifier": isbn}],
    }
    volume.update(volume_overrides)
    return {"items": [{"id": "one", "volumeInfo": volume}]}


def test_key_uses_params_partial_fields_and_never_leaks_to_result_or_url_argument():
    captured: dict[str, Any] = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            200,
            _payload(title=f"Title {SENTINEL}", infoLink=f"https://example.invalid/{SENTINEL}"),
        )

    metadata, found_isbn, warning = google_books.search_google_books(
        f"isbn:{ISBN}",
        requested_isbn=ISBN,
        api_key=SENTINEL,
        request_get=fake_get,
        max_retries=0,
    )

    assert captured["url"] == google_books.GOOGLE_BOOKS_URL
    assert SENTINEL not in captured["url"]
    assert captured["params"]["key"] == SENTINEL
    assert "volumeInfo" in captured["params"]["fields"]
    assert captured["timeout"] == 12
    assert found_isbn == ISBN and warning is None
    assert SENTINEL not in json.dumps(metadata)


def test_request_exception_is_secret_safe_and_bounded_without_network_or_sleep():
    calls = 0
    sleeps: list[float] = []

    def failing_get(_url, **_kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError(f"transport included {SENTINEL}")

    result = google_books.search_google_books(
        "intitle:test",
        api_key=SENTINEL,
        request_get=failing_get,
        sleep=sleeps.append,
        delay_ms=100,
        max_retries=2,
        max_retry_after_sec=5,
    )

    assert calls == 3
    assert sleeps == [0.1, 0.2]
    assert SENTINEL not in json.dumps(result)


def test_429_respects_numeric_retry_after_with_safe_cap():
    responses = [
        FakeResponse(429, {}, {"Retry-After": "99"}),
        FakeResponse(200, _payload()),
    ]
    sleeps: list[float] = []

    result = google_books.search_google_books(
        f"isbn:{ISBN}",
        requested_isbn=ISBN,
        request_get=lambda *_args, **_kwargs: responses.pop(0),
        sleep=sleeps.append,
        max_retries=1,
        max_retry_after_sec=3,
    )

    assert result[0] is not None and result[2] is None
    assert sleeps == [3.0]


@pytest.mark.parametrize("status_code", [500, 502, 503, 599])
def test_transient_5xx_retries_then_succeeds(status_code: int):
    responses = [FakeResponse(status_code, {}), FakeResponse(200, _payload())]
    sleeps: list[float] = []
    metadata, _found, warning = google_books.search_google_books(
        f"isbn:{ISBN}",
        requested_isbn=ISBN,
        request_get=lambda *_args, **_kwargs: responses.pop(0),
        sleep=sleeps.append,
        delay_ms=50,
        max_retries=1,
    )
    assert metadata is not None and warning is None
    assert sleeps == [0.05]


@pytest.mark.parametrize("status_code", [400, 403, 404])
def test_ordinary_4xx_does_not_retry(status_code: int):
    calls = 0

    def fake_get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeResponse(status_code, {"error": SENTINEL})

    result = google_books.search_google_books(
        "intitle:test",
        api_key=SENTINEL,
        request_get=fake_get,
        sleep=lambda _seconds: pytest.fail("ordinary 4xx must not sleep"),
        max_retries=4,
    )
    assert calls == 1
    assert result[0] is None
    assert result[2] == f"google books http {status_code}"
    assert SENTINEL not in json.dumps(result)


def test_isbn_search_rejects_mismatching_identifier_but_accepts_missing_identifiers():
    mismatch = google_books.parse_google_books_response(_payload(OTHER_ISBN), requested_isbn=ISBN)
    no_identifiers = google_books.parse_google_books_response(
        _payload(ISBN, industryIdentifiers=[]), requested_isbn=ISBN
    )
    assert mismatch[0] is None
    assert mismatch[2] == "google books returned a mismatching ISBN"
    assert no_identifiers[0] is not None and no_identifiers[2] is None


def test_response_normalization_is_defensive():
    metadata, found, warning = google_books.parse_google_books_response(
        _payload(ISBN, authors="not-a-list", categories=["One", "One"], pageCount="0")
    )
    assert warning is None and found == ISBN
    assert metadata is not None
    assert metadata["authors"] == []
    assert metadata["categories"] == ["One"]
    assert metadata["page_count"] is None
    assert metadata["cover_image"].startswith("https://")
    assert "zoom=2" in metadata["cover_image"]


def test_photo_and_migration_wrappers_call_shared_client(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, dict]] = []

    def fake_search(query: str, **kwargs):
        calls.append((query, kwargs))
        return _normalized_metadata(), ISBN, None

    monkeypatch.setattr(resolve_metadata, "search_google_books", fake_search)
    monkeypatch.setattr(migrate_goodreads_csv, "search_google_books", fake_search)

    photo_metadata, photo_warning = resolve_metadata._from_google_books(ISBN, 3, "test-agent")
    migration_metadata, migration_isbn, migration_warning = migrate_goodreads_csv._google_books_enrich(
        "Test Book", "Test Author", ISBN, 3, 0, 0, ""
    )

    assert photo_metadata and photo_warning is None
    assert migration_metadata and migration_isbn == ISBN and migration_warning is None
    assert [query for query, _kwargs in calls] == [f"isbn:{ISBN}", f"isbn:{ISBN}"]


def _normalized_metadata() -> dict:
    return {
        "authors": ["Test Author"],
        "categories": ["Testing"],
        "cover_image": None,
        "description": "Description",
        "language": "en",
        "page_count": 200,
        "published_date": "2024",
        "publisher": "Test Press",
        "source": "google_books",
        "source_url": None,
        "title": "Test Book",
    }
