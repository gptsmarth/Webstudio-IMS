"""Client update platform API — LAN clients consume updates from WEBSTUDIO Server only."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.client_updates import ClientUpdateCheckResponse
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.services.client_update_service import ClientUpdateService

router = APIRouter(prefix="/api/v1/client-updates", tags=["client-updates"])


def _parse_channel(value: str | None) -> ReleaseChannel | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized not in {item.value for item in ReleaseChannel}:
        return None
    return ReleaseChannel(normalized)


@router.get(
    "/check",
    summary="Check for client updates",
    description=(
        "Compare installed client version against the enterprise release catalog. "
        "Clients must never contact GitHub directly — this server is the update authority."
    ),
)
async def client_updates_check(
    request: Request,
    platform: Literal["desktop_windows", "desktop_macos", "mobile_android", "mobile_ios"] = Query(
        ...,
        description="Client platform identifier",
    ),
    current_version: str = Query(..., min_length=1, max_length=32),
    channel: Literal["development", "beta", "stable"] | None = Query(default=None),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = ClientUpdateService(db_session, app_settings)
    payload = await service.check_for_updates(
        platform=platform,
        current_version=current_version,
        channel=_parse_channel(channel),
    )
    return build_envelope(request, ClientUpdateCheckResponse(**payload).model_dump())


@router.get(
    "/download",
    summary="Download client update artifact",
    description="Stream a validated release artifact from the enterprise update server.",
)
async def client_updates_download(
    platform: Literal["desktop_windows", "desktop_macos", "mobile_android"] = Query(...),
    release_version: str = Query(..., min_length=1, max_length=32),
    build_number: int = Query(..., ge=1),
    channel: Literal["development", "beta", "stable"] | None = Query(default=None),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> FileResponse:
    service = ClientUpdateService(db_session, app_settings)
    try:
        path = await service.resolve_artifact_file(
            platform=platform,
            release_version=release_version,
            build_number=build_number,
            channel=_parse_channel(channel),
        )
        checksum = await service.get_artifact_checksum(
            platform=platform,
            release_version=release_version,
            build_number=build_number,
            channel=_parse_channel(channel),
            artifact_name=path.name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    headers = {}
    if checksum:
        headers["X-Artifact-SHA256"] = checksum

    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
        headers=headers,
    )
