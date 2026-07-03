"""Office deployment wizard endpoints (M12F)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import NetworkAdminDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.deployment import (
    IpStrategyRecommendationEntry,
    OfficeDeploymentApplyResponse,
    OfficeDeploymentCompleteResponse,
    OfficeDeploymentDetectionResponse,
    OfficeDeploymentStatusResponse,
)
from webstudio_backend.api.schemas.network import NetworkValidationCheckEntry
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.services.office_deployment_service import (
    OfficeDeploymentDetection,
    OfficeDeploymentService,
)

router = APIRouter(prefix="/api/v1/deployment/office", tags=["deployment"])


def _mdns_active(request: Request) -> bool:
    mdns = getattr(request.app.state, "mdns_service", None)
    if mdns is None:
        return False
    return bool(getattr(mdns, "_started", False))


def _detection_payload(detection: OfficeDeploymentDetection) -> OfficeDeploymentDetectionResponse:
    ip_strategy = None
    if detection.ip_strategy is not None:
        ip_strategy = IpStrategyRecommendationEntry(**detection.ip_strategy.to_dict())
    return OfficeDeploymentDetectionResponse(
        generated_at=detection.generated_at,
        overall_status=detection.overall_status,
        checks=[NetworkValidationCheckEntry(**asdict(check)) for check in detection.checks],
        recommendations=detection.recommendations,
        ip_strategy=ip_strategy,
        server_lan_ip=detection.server_lan_ip,
        hostname=detection.hostname,
        data_root=detection.data_root,
        api_port=detection.api_port,
    )


@router.get(
    "/status",
    summary="Office deployment wizard completion status",
)
async def office_deployment_status(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = OfficeDeploymentService(db_session, app_settings)
    raw = await service.get_status()
    payload = OfficeDeploymentStatusResponse(**raw)
    return build_envelope(request, payload.model_dump())


@router.post(
    "/detect",
    summary="Run office deployment environment detection",
)
async def office_deployment_detect(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = OfficeDeploymentService(db_session, app_settings)
    detection = await service.detect(mdns_active=_mdns_active(request))
    payload = _detection_payload(detection)
    return build_envelope(request, payload.model_dump())


@router.post(
    "/apply",
    summary="Apply recommended office deployment configuration",
)
async def office_deployment_apply(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = OfficeDeploymentService(db_session, app_settings)
    result = await service.apply_recommended_configuration(actor_id=current.user.id)
    await db_session.commit()
    payload = OfficeDeploymentApplyResponse(
        saved_settings=result.saved_settings,
        created_directories=result.created_directories,
        messages=result.messages,
    )
    return build_envelope(request, payload.model_dump())


@router.post(
    "/complete",
    summary="Detect, apply configuration, and finalize deployment summary",
)
async def office_deployment_complete(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = OfficeDeploymentService(db_session, app_settings)
    detection, apply_result, summary = await service.complete_deployment(
        mdns_active=_mdns_active(request),
        actor_id=current.user.id,
    )
    await db_session.commit()
    payload = OfficeDeploymentCompleteResponse(
        detection=_detection_payload(detection),
        apply=OfficeDeploymentApplyResponse(
            saved_settings=apply_result.saved_settings,
            created_directories=apply_result.created_directories,
            messages=apply_result.messages,
        ),
        summary=summary,
        completed=True,
        completed_at=datetime.now(UTC).isoformat(),
    )
    return build_envelope(request, payload.model_dump())


@router.get(
    "/summary",
    summary="Retrieve persisted office deployment summary",
)
async def office_deployment_summary(
    request: Request,
    current: NetworkAdminDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    service = OfficeDeploymentService(db_session, app_settings)
    status = await service.get_status()
    return build_envelope(request, {"summary": status.get("summary")})
