"""Pagination helper unit tests."""

from __future__ import annotations

import pytest

from webstudio_backend.infrastructure.database.repositories.pagination import PageParams


def test_page_params_offset() -> None:
    params = PageParams(page=2, page_size=25)
    assert params.offset == 25


def test_page_params_rejects_invalid_page() -> None:
    with pytest.raises(ValueError):
        PageParams(page=0)
