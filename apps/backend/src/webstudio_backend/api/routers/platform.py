"""Platform discovery endpoints — version and capabilities."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.config import Settings
from webstudio_backend.services.client_update_service import ClientUpdateService
from webstudio_backend.services.platform_info_service import (
    build_capabilities_payload,
)

router = APIRouter(prefix="/api/v1", tags=["platform"])


@router.get(
    "/version",
    summary="API and backend version information",
    description=(
        "Returns backend, schema, API, and build version metadata plus minimum supported "
        "desktop and mobile client versions. Public endpoint for client compatibility checks."
    ),
)
async def api_version(
    request: Request,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await ClientUpdateService(db_session, app_settings).build_enriched_version_payload()
    return build_envelope(request, payload)


@router.get(
    "/capabilities",
    summary="Enabled modules and feature flags",
    description=(
        "Returns installed version, enabled modules, AI provider configuration, "
        "and feature flags. Public endpoint for client capability discovery."
    ),
)
async def api_capabilities(request: Request, db_session: AsyncSession = DbSessionDep) -> dict:
    settings = request.app.state.settings
    payload = await build_capabilities_payload(db_session, settings)
    return build_envelope(request, payload)
