"""Unified search API for multi-client global search."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import CurrentUserDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.services.global_search_service import global_search

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get(
    "",
    summary="Global search",
    description=(
        "Search inventory, brands, locations, and product models in one request. "
        "Replaces client-side multi-fetch search for mobile and web clients."
    ),
)
async def search_all(
    request: Request,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    q: str = Query(min_length=1, max_length=128),
    types: list[str] | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=25),
) -> dict:
    del current
    payload = await global_search(db_session, query=q, types=types, limit=limit)
    return build_envelope(request, payload)
