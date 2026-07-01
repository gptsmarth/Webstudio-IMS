"""Shared API response helpers for envelope and pagination meta."""

from __future__ import annotations

from fastapi import Request

from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.request_context import get_correlation_id, get_request_id


def build_envelope(
    request: Request,
    data: object,
    meta: ResponseMeta | None = None,
) -> dict:
    """Build the standard success envelope for JSON API responses."""
    return Envelope(
        data=data,
        meta=meta,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def build_page_meta(
    page: int,
    page_size: int,
    total_items: int,
    total_pages: int,
    *,
    include_legacy_aliases: bool = False,
) -> ResponseMeta:
    """Build standardized pagination metadata for list endpoints."""
    has_next = page < total_pages if total_pages > 0 else False
    has_previous = page > 1 and total_pages > 0
    return ResponseMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        has_more=has_next,
        total_records=total_items if include_legacy_aliases else None,
        current_page=page if include_legacy_aliases else None,
    )
