"""Client deployment commissioning API (M14E)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import NetworkAdminDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.services.client_deployment_validation_service import (
    ClientDeploymentValidationService,
)
from webstudio_backend.services.production_acceptance_validation_service import (
    ProductionAcceptanceValidationService,
)
from webstudio_backend.services.production_certification_validation_service import (
    ProductionCertificationValidationService,
)
from webstudio_backend.services.final_production_handover_validation_service import (
    FinalProductionHandoverValidationService,
)

router = APIRouter(prefix="/api/v1/deployment", tags=["deployment"])


@router.get(
    "/client-validation",
    summary="Run M14E production client deployment validation",
)
async def client_deployment_validation(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = ClientDeploymentValidationService(db_session, app_settings)
    payload = await service.build_production_report()
    return build_envelope(request, payload)


@router.get(
    "/production-acceptance",
    summary="Run M14F complete production acceptance validation",
)
async def production_acceptance_validation(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = ProductionAcceptanceValidationService(db_session, app_settings)
    payload = await service.build_acceptance_report()
    return build_envelope(request, payload)


@router.get(
    "/production-certification",
    summary="Run M14G production security, performance, and infrastructure certification",
)
async def production_certification_validation(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = ProductionCertificationValidationService(db_session, app_settings)
    payload = await service.build_certification_report()
    return build_envelope(request, payload)


@router.get(
    "/production-handover",
    summary="Run M14J final production handover validation (v1.0.0)",
)
async def production_handover_validation(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = FinalProductionHandoverValidationService(db_session, app_settings)
    payload = await service.build_handover_report()
    return build_envelope(request, payload)
