"""Offline sync preparation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import CurrentUserDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.services.sync_state_service import build_sync_state

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get(
    "/state",
    summary="Sync state and high-water marks",
    description=(
        "Returns server time, schema version, and per-entity high-water marks for "
        "mobile offline-sync preparation. Authenticated clients should poll periodically."
    ),
)
async def sync_state(
    request: Request,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    settings = request.app.state.settings
    payload = await build_sync_state(db_session, app_version=settings.app_version)
    return build_envelope(request, payload)
