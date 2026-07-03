"""Enterprise release management API — server-side update metadata authority."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import SettingsViewDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.releases import (
    ReleaseDownloadHistoryResponse,
    ReleaseHistoryResponse,
    ReleaseMetadataResponse,
    ReleaseSyncStatusResponse,
)
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.github_release_sync_service import GitHubReleaseSyncService

router = APIRouter(prefix="/api/v1/releases", tags=["releases"])


def _parse_channel(value: str | None) -> ReleaseChannel | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized not in {item.value for item in ReleaseChannel}:
        return None
    return ReleaseChannel(normalized)


@router.get(
    "/current",
    summary="Currently installed / active server release",
    description=(
        "Returns release metadata for the version running on this WEBSTUDIO Server, "
        "including compatibility matrix and checksum catalog. Public read-only endpoint."
    ),
)
async def releases_current(
    request: Request,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await EnterpriseReleaseService(db_session, app_settings).get_current_release()
    return build_envelope(request, ReleaseMetadataResponse(**payload).model_dump())


@router.get(
    "/latest",
    summary="Latest published release for a channel",
    description=(
        "Returns the newest release published on this update server for the requested channel. "
        "Clients must not contact GitHub directly — this endpoint is the distribution authority."
    ),
)
async def releases_latest(
    request: Request,
    channel: Literal["development", "beta", "stable"] | None = Query(default=None),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = EnterpriseReleaseService(db_session, app_settings)
    payload = await service.get_latest_release(_parse_channel(channel))
    return build_envelope(request, ReleaseMetadataResponse(**payload).model_dump())


@router.get(
    "/history",
    summary="Published release history",
    description="Paginated release history for a channel on this enterprise update server.",
)
async def releases_history(
    request: Request,
    channel: Literal["development", "beta", "stable"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = EnterpriseReleaseService(db_session, app_settings)
    payload = await service.get_release_history(
        channel=_parse_channel(channel),
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, ReleaseHistoryResponse(**payload).model_dump())


@router.get(
    "/sync/status",
    summary="GitHub release synchronization status",
    description=(
        "Administrator endpoint reporting GitHub polling state, download queue counts, "
        "and update storage location. Downloads never auto-deploy."
    ),
)
async def releases_sync_status(
    request: Request,
    _admin: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await GitHubReleaseSyncService(db_session, app_settings).get_sync_status()
    return build_envelope(request, ReleaseSyncStatusResponse(**payload).model_dump())


@router.get(
    "/sync/history",
    summary="Completed GitHub release download history",
    description="Paginated history of successfully downloaded GitHub releases awaiting administrator approval.",
)
async def releases_sync_history(
    request: Request,
    _admin: SettingsViewDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await GitHubReleaseSyncService(db_session, app_settings).get_download_history(
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, ReleaseDownloadHistoryResponse(**payload).model_dump())


@router.get(
    "/sync/failures",
    summary="Failed GitHub release download history",
    description="Paginated history of failed or skipped GitHub release download attempts.",
)
async def releases_sync_failures(
    request: Request,
    _admin: SettingsViewDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await GitHubReleaseSyncService(db_session, app_settings).get_failed_history(
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, ReleaseDownloadHistoryResponse(**payload).model_dump())
