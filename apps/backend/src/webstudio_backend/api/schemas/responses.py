"""API response schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ResponseMeta(BaseModel):
    page: int | None = None
    page_size: int | None = None
    total_items: int | None = None
    total: int | None = None
    total_pages: int | None = None
    has_next: bool | None = None
    has_previous: bool | None = None
    # Legacy aliases — prefer total_items / page; kept for backward compatibility.
    total_records: int | None = None
    current_page: int | None = None
    next_cursor: str | None = None
    has_more: bool | None = None


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta | None = None
    request_id: str
    correlation_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
