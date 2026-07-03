"""Enterprise network administration endpoints."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import NetworkAdminDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.network import (
    NetworkReportResponse,
    NetworkValidationCheckEntry,
    NetworkValidationResponse,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.services.network_validation_service import NetworkValidationService

router = APIRouter(prefix="/api/v1/network/admin", tags=["network"])

ValidationScope = Literal["standard", "production"]


def _mdns_active(request: Request) -> bool:
    mdns = getattr(request.app.state, "mdns_service", None)
    if mdns is None:
        return False
    return bool(getattr(mdns, "_started", False))


@router.post(
    "/validate",
    summary="Run administrator network validation wizard",
)
async def network_admin_validate(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    scope: ValidationScope = Query(
        default="standard",
        description="Use production for M14B LAN commissioning checks.",
    ),
) -> dict:
    _ = current
    service = NetworkValidationService(db_session, app_settings)
    if scope == "production":
        report = await service.run_production_network_validation(mdns_active=_mdns_active(request))
        validation_scope = "production"
    else:
        report = await service.run_admin_validation(mdns_active=_mdns_active(request))
        validation_scope = "standard"
    payload = NetworkValidationResponse(
        generated_at=report.generated_at,
        overall_status=report.overall_status,
        topology=report.topology,
        checks=[NetworkValidationCheckEntry(**asdict(check)) for check in report.checks],
        recommendations=report.recommendations,
        validation_scope=validation_scope,
    )
    return build_envelope(request, payload.model_dump())


@router.get(
    "/report",
    summary="Generate enterprise network report",
)
async def network_admin_report(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    scope: ValidationScope = Query(
        default="standard",
        description="Use production for M14B network validation report payload.",
    ),
) -> dict:
    _ = current
    service = NetworkValidationService(db_session, app_settings)
    if scope == "production":
        raw = await service.build_production_network_report(mdns_active=_mdns_active(request))
    else:
        raw = await service.build_network_report(mdns_active=_mdns_active(request))
        raw["validation_scope"] = "standard"
    payload = NetworkReportResponse(**raw)
    return build_envelope(request, payload.model_dump())
