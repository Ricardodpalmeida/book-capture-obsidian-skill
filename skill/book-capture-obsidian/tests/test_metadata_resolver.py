from __future__ import annotations

from typing import Any, Callable, Dict, List

import pytest

from metadata_cache import MetadataCache
from metadata_resolver import MetadataResolver, merge_missing

ISBN = "9780306406157"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def openlibrary_book(description: str | None = "An OL description", cover: bool = True) -> dict:
    book: Dict[str, Any] = {
        "title": "Test Book",
        "authors": [{"name": "Test Author"}],
        "publishers": [{"name": "Test Press"}],
        "publish_date": "2024",
        "number_of_pages": 200,
        "subjects": [{"name": "Testing"}],
        "url": "https://openlibrary.org/books/OL1M/Test_Book",
    }
    if description:
        book["description"] = description
    if cover:
        book["cover"] = {"large": "https://covers.openlibrary.org/b/id/1-L.jpg"}
    return {f"ISBN:{ISBN}": book}


def google_payload() -> dict:
    return {
        "items": [
            {
                "volumeInfo": {
                    "title": "Test Book (Google)",
                    "authors": ["Test Author"],
                    "description": "A Google description",
                    "imageLinks": {"thumbnail": "https://books.google.test/c?zoom=1"},
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": ISBN}],
                }
            }
        ]
    }


def router(routes: Dict[str, Callable[[], FakeResponse]], log: List[str]):
    def fake_get(url, **_kwargs):
        log.append(url)
        for prefix, make in routes.items():
            if url.startswith(prefix):
                return make()
        raise AssertionError(f"unexpected URL {url}")

    return fake_get


def make_resolver(fake_get, clock: Clock, cache: MetadataCache | None = None, **kwargs) -> MetadataResolver:
    return MetadataResolver(
        cache=cache or MetadataCache(None, now=clock.now),
        request_get=fake_get,
        sleep=clock.sleep,
        now=clock.now,
        **kwargs,
    )


def test_complete_openlibrary_result_never_calls_google():
    clock, log = Clock(), []
    fake_get = router({"https://openlibrary.org/api/books": lambda: FakeResponse(200, openlibrary_book())}, log)
    resolver = make_resolver(fake_get, clock)

    metadata, isbn, warnings = resolver.lookup(isbn13=ISBN)

    assert metadata["title"] == "Test Book" and metadata["description"] == "An OL description"
    assert isbn == ISBN and warnings == []
    assert resolver.stats.network_calls == {"openlibrary": 1, "google_books": 0}


def test_google_only_fills_missing_fields_without_overwriting():
    clock, log = Clock(), []
    fake_get = router(
        {
            "https://openlibrary.org/api/books": lambda: FakeResponse(200, openlibrary_book(description=None)),
            "https://www.googleapis.com/books/v1/volumes": lambda: FakeResponse(200, google_payload()),
        },
        log,
    )
    resolver = make_resolver(fake_get, clock)

    metadata, _isbn, _warnings = resolver.lookup(isbn13=ISBN)

    assert metadata["title"] == "Test Book"  # Open Library value kept
    assert metadata["description"] == "A Google description"  # gap filled
    assert metadata["source"] == "openlibrary"


def test_second_lookup_is_served_from_persistent_cache(tmp_path):
    clock, log = Clock(), []
    fake_get = router({"https://openlibrary.org/api/books": lambda: FakeResponse(200, openlibrary_book())}, log)
    path = tmp_path / "cache.sqlite3"

    first = make_resolver(fake_get, clock, MetadataCache(path, now=clock.now))
    first.lookup(isbn13=ISBN)
    second = make_resolver(fake_get, clock, MetadataCache(path, now=clock.now))
    metadata, _isbn, _warnings = second.lookup(isbn13=ISBN)

    assert metadata["title"] == "Test Book"
    assert len(log) == 1
    assert second.stats.cache_hits == 1 and second.stats.network_calls["openlibrary"] == 0


def test_google_429_pauses_google_for_later_rows_and_later_runs(tmp_path):
    clock, log = Clock(), []
    fake_get = router(
        {
            "https://openlibrary.org/api/books": lambda: FakeResponse(200, openlibrary_book(description=None)),
            "https://www.googleapis.com/books/v1/volumes": lambda: FakeResponse(429, {}),
        },
        log,
    )
    path = tmp_path / "cache.sqlite3"
    resolver = make_resolver(fake_get, clock, MetadataCache(path, now=clock.now), google_max_retries=1)

    _m, _i, first_warnings = resolver.lookup(isbn13=ISBN)
    _m, _i, second_warnings = resolver.lookup(isbn13="9780201633610")
    google_calls = [url for url in log if "googleapis" in url]

    assert len(google_calls) == 2  # one request plus one retry, then nothing
    assert any("paused" in w for w in first_warnings)
    assert any("cooling down" in w for w in second_warnings)

    next_run = make_resolver(fake_get, clock, MetadataCache(path, now=clock.now))
    next_run.lookup(isbn13="9780131103627")
    assert len([url for url in log if "googleapis" in url]) == 2
    assert next_run.stats.google_skipped_cooldown == 1

    clock.t += 3601
    after_cooldown = make_resolver(fake_get, clock, MetadataCache(path, now=clock.now), google_max_retries=0)
    after_cooldown.lookup(isbn13="9780131103627")
    assert len([url for url in log if "googleapis" in url]) == 3


def test_per_run_google_budget_is_enforced():
    clock, log = Clock(), []
    fake_get = router(
        {
            "https://openlibrary.org/api/books": lambda: FakeResponse(200, {}),
            "https://www.googleapis.com/books/v1/volumes": lambda: FakeResponse(200, {"items": []}),
        },
        log,
    )
    resolver = make_resolver(fake_get, clock, google_budget=2)
    for isbn in ["9780306406157", "9780201633610", "9780131103627"]:
        resolver.lookup(isbn13=isbn)

    assert resolver.stats.network_calls["google_books"] == 2
    assert resolver.stats.google_skipped_budget == 1


def test_transient_errors_are_not_cached():
    clock, log = Clock(), []
    responses = [FakeResponse(503, {}), FakeResponse(200, openlibrary_book())]
    fake_get = router({"https://openlibrary.org/api/books": lambda: responses.pop(0)}, log)
    resolver = make_resolver(fake_get, clock, providers=["openlibrary"])

    failed, _i, warnings = resolver.lookup(isbn13=ISBN)
    retried, _i, _w = resolver.lookup(isbn13=ISBN)

    assert failed is None and warnings == ["openlibrary request failed"]
    assert retried is not None and retried["title"] == "Test Book"


def test_openlibrary_requests_are_spaced():
    clock, log = Clock(), []
    fake_get = router({"https://openlibrary.org/api/books": lambda: FakeResponse(200, openlibrary_book())}, log)
    resolver = make_resolver(fake_get, clock, providers=["openlibrary"], openlibrary_delay_ms=500)
    start = clock.t
    resolver.lookup(isbn13="9780306406157")
    resolver.lookup(isbn13="9780201633610")
    assert clock.t - start == pytest.approx(0.5)


def test_base_fields_win_and_title_search_does_not_adopt_edition_isbn():
    clock, log = Clock(), []
    search = {"docs": [{"key": "/works/OL1W", "title": "CSV Title: A Novel", "author_name": ["Csv Author"], "cover_i": 7}]}
    fake_get = router(
        {
            "https://openlibrary.org/search.json": lambda: FakeResponse(200, search),
            "https://openlibrary.org/works/OL1W.json": lambda: FakeResponse(200, {"description": {"value": "Work text"}}),
        },
        log,
    )
    resolver = make_resolver(fake_get, clock, providers=["openlibrary"])
    base = {"title": "CSV Title", "authors": ["CSV Author"], "description": None, "cover_image": None}

    metadata, isbn, _w = resolver.lookup(title="CSV Title", author="CSV Author", base=base)

    assert metadata["title"] == "CSV Title" and metadata["authors"] == ["CSV Author"]
    assert metadata["description"] == "Work text"
    assert metadata["cover_image"] == "https://covers.openlibrary.org/b/id/7-L.jpg"
    assert isbn is None


def test_merge_missing_ignores_empty_values():
    assert merge_missing({"title": "A", "categories": []}, {"title": "B", "categories": ["x"], "publisher": ""}) == {
        "title": "A",
        "categories": ["x"],
    }


def test_title_search_rejects_wrong_book_and_picks_matching_doc():
    # Shapes taken from real Open Library responses (2026-10): a title plus
    # author query for "The Three-Body Problem" ranks the sequels first, and a
    # title-only query returns a physics book with the same title.
    clock, log = Clock(), []
    docs = {
        "docs": [
            {"key": "/works/OL16314245W", "title": "The Dark Forest (The Three-Body Problem Series Book 2)", "author_name": ["Liu Cixin"]},
            {"key": "/works/OL15172337W", "title": "The Three-Body Problem", "author_name": ["Mauri Valtonen", "Hannu Karttunen"]},
            {"key": "/works/OL9W", "title": "The Three-Body Problem", "author_name": ["Cixin Liu"], "cover_i": 3},
        ]
    }
    fake_get = router(
        {
            "https://openlibrary.org/search.json": lambda: FakeResponse(200, docs),
            "https://openlibrary.org/works/OL9W.json": lambda: FakeResponse(200, {"description": "Right book"}),
        },
        log,
    )
    resolver = make_resolver(fake_get, clock, providers=["openlibrary"])
    metadata, _isbn, _w = resolver.lookup(title="The Three-Body Problem", author="Liu Cixin")
    assert metadata["description"] == "Right book"
    assert "limit=5" in log[0]

    only_wrong = {"docs": docs["docs"][:2]}
    fake_get = router({"https://openlibrary.org/search.json": lambda: FakeResponse(200, only_wrong)}, [])
    resolver = make_resolver(fake_get, Clock(), providers=["openlibrary"])
    metadata, _isbn, warnings = resolver.lookup(title="The Three-Body Problem", author="Liu Cixin")
    assert not (metadata or {}).get("description")
    assert any("no close title/author match" in w for w in warnings)


def test_isbn_lookup_follows_edition_record_to_work_description():
    # Real jscmd=data responses carry the edition key but no works link.
    clock, log = Clock(), []
    book = openlibrary_book(description=None)
    book[f"ISBN:{ISBN}"]["key"] = "/books/OL1M"
    book[f"ISBN:{ISBN}"]["subjects"] = [{"name": f"S{i}"} for i in range(30)]
    fake_get = router(
        {
            "https://openlibrary.org/api/books": lambda: FakeResponse(200, book),
            "https://openlibrary.org/books/OL1M.json": lambda: FakeResponse(200, {"works": [{"key": "/works/OL7W"}]}),
            "https://openlibrary.org/works/OL7W.json": lambda: FakeResponse(200, {"description": {"value": "Work blurb"}}),
        },
        log,
    )
    resolver = make_resolver(fake_get, clock, providers=["openlibrary"])
    metadata, _isbn, _w = resolver.lookup(isbn13=ISBN)
    assert metadata["description"] == "Work blurb"
    assert len(metadata["categories"]) == 10
    assert [u.split("?")[0] for u in log] == [
        "https://openlibrary.org/api/books",
        "https://openlibrary.org/books/OL1M.json",
        "https://openlibrary.org/works/OL7W.json",
    ]


def test_google_title_search_needs_matching_title_and_drops_isbn():
    clock = Clock()
    wrong = google_payload()
    fake_get = router(
        {
            "https://openlibrary.org/search.json": lambda: FakeResponse(200, {"docs": []}),
            "https://www.googleapis.com/books/v1/volumes": lambda: FakeResponse(200, wrong),
        },
        [],
    )
    resolver = make_resolver(fake_get, clock, google_delay_ms=0)
    metadata, isbn, warnings = resolver.lookup(title="Completely Different", author="Someone")
    assert not (metadata or {}).get("description") and isbn is None
    assert any("google books found no close" in w for w in warnings)

    resolver = make_resolver(fake_get, Clock(), google_delay_ms=0)
    metadata, isbn, _w = resolver.lookup(title="Test Book", author="Test Author")
    assert metadata["description"] == "A Google description"
    assert isbn is None
