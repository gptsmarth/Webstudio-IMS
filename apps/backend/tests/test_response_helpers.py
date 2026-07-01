"""Response helper unit tests."""

from __future__ import annotations

from webstudio_backend.api.response_helpers import build_page_meta


def test_build_page_meta_first_page() -> None:
    meta = build_page_meta(page=1, page_size=50, total_items=120, total_pages=3)
    assert meta.page == 1
    assert meta.page_size == 50
    assert meta.total_items == 120
    assert meta.total == 120
    assert meta.total_pages == 3
    assert meta.has_next is True
    assert meta.has_previous is False
    assert meta.has_more is True


def test_build_page_meta_last_page() -> None:
    meta = build_page_meta(page=3, page_size=50, total_items=120, total_pages=3)
    assert meta.has_next is False
    assert meta.has_previous is True
    assert meta.has_more is False


def test_build_page_meta_empty() -> None:
    meta = build_page_meta(page=1, page_size=50, total_items=0, total_pages=0)
    assert meta.has_next is False
    assert meta.has_previous is False


def test_build_page_meta_legacy_aliases() -> None:
    meta = build_page_meta(page=2, page_size=25, total_items=40, total_pages=2, include_legacy_aliases=True)
    assert meta.total_records == 40
    assert meta.current_page == 2
