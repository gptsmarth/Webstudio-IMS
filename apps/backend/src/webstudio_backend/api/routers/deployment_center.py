"""Deployment Center API — administrator release lifecycle control (M13C)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import CurrentUserDep, SettingsModifyDep, SettingsViewDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.deployment_center import (
    DeploymentActionRequest,
    DeploymentAnalyticsResponse,
    DeploymentCenterDashboard,
    DeploymentEventHistoryResponse,
    DeploymentRunResponse,
    RollbackHistoryResponse,
    RollbackRunResponse,
)
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.config import Settings
from webstudio_backend.services.deployment_center_service import DeploymentCenterService

router = APIRouter(prefix="/api/v1/deployment/center", tags=["deployment"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/analytics",
    summary="Enterprise deployment monitoring analytics",
    description=(
        "Aggregated deployment monitoring for release downloads, deployment and rollback history, "
        "health checks, client version distribution, failures, retry queue, and scheduler recovery."
    ),
)
async def deployment_center_analytics(
    request: Request,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_analytics()
    return build_envelope(request, DeploymentAnalyticsResponse(**payload).model_dump())


@router.get(
    "/dashboard",
    summary="Deployment Center dashboard",
    description="Release versions, compatibility, downloaded packages, and deployment status.",
)
async def deployment_center_dashboard(
    request: Request,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_dashboard()
    return build_envelope(request, DeploymentCenterDashboard(**payload).model_dump())


@router.get(
    "/history",
    summary="Deployment history",
)
async def deployment_center_history(
    request: Request,
    _viewer: SettingsViewDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_deployment_history(
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, DeploymentEventHistoryResponse(**payload).model_dump())


@router.get(
    "/logs",
    summary="Deployment operation logs",
)
async def deployment_center_logs(
    request: Request,
    _viewer: SettingsViewDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_deployment_logs(
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, DeploymentEventHistoryResponse(**payload).model_dump())


@router.post("/check-updates", summary="Check GitHub for newer releases")
async def deployment_check_updates(
    request: Request,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        payload = await DeploymentCenterService(db_session, app_settings).check_updates(
            user_id=current.user.id,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/download", summary="Download pending release packages")
async def deployment_download(
    request: Request,
    body: DeploymentActionRequest,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        payload = await DeploymentCenterService(db_session, app_settings).download_updates(
            user_id=current.user.id,
            job_id=body.job_id,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/validate", summary="Validate a downloaded release package")
async def deployment_validate(
    request: Request,
    body: DeploymentActionRequest,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    if body.job_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="job_id is required")
    try:
        payload = await DeploymentCenterService(db_session, app_settings).validate_package(
            user_id=current.user.id,
            job_id=body.job_id,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get(
    "/runs/latest",
    summary="Latest deployment run status",
)
async def deployment_latest_run(
    request: Request,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_latest_deployment_run()
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No deployment runs found")
    return build_envelope(request, DeploymentRunResponse(**payload).model_dump())


@router.get(
    "/runs/{run_id}",
    summary="Deployment run step progress",
)
async def deployment_run_status(
    request: Request,
    run_id: int,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        payload = await DeploymentCenterService(db_session, app_settings).get_deployment_run(run_id)
        return build_envelope(request, DeploymentRunResponse(**payload).model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/deploy",
    summary="Deploy a validated release (requires administrator approval)",
)
async def deployment_deploy(
    request: Request,
    body: DeploymentActionRequest,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    if body.job_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="job_id is required")
    try:
        payload = await DeploymentCenterService(db_session, app_settings).deploy_release(
            user_id=current.user.id,
            job_id=body.job_id,
            administrator_approved=body.administrator_approved,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post(
    "/rollback",
    summary="Rollback to previous release (requires administrator approval)",
)
async def deployment_rollback(
    request: Request,
    body: DeploymentActionRequest,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        payload = await DeploymentCenterService(db_session, app_settings).rollback_release(
            user_id=current.user.id,
            administrator_approved=body.administrator_approved,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get(
    "/rollback/history",
    summary="Permanent enterprise rollback history",
)
async def deployment_rollback_history(
    request: Request,
    _viewer: SettingsViewDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_rollback_history(
        page=page,
        page_size=page_size,
    )
    return build_envelope(request, RollbackHistoryResponse(**payload).model_dump())


@router.get(
    "/rollback/runs/{run_id}",
    summary="Enterprise rollback run detail",
)
async def deployment_rollback_run(
    request: Request,
    run_id: int,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        payload = await DeploymentCenterService(db_session, app_settings).get_rollback_run(run_id)
        return build_envelope(request, RollbackRunResponse(**payload).model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/delete-package",
    summary="Delete a downloaded package (requires administrator approval)",
)
async def deployment_delete_package(
    request: Request,
    body: DeploymentActionRequest,
    current: CurrentUserDep,
    _admin: SettingsModifyDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    if body.job_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="job_id is required")
    try:
        payload = await DeploymentCenterService(db_session, app_settings).delete_package(
            user_id=current.user.id,
            job_id=body.job_id,
            administrator_approved=body.administrator_approved,
        )
        await db_session.commit()
        return build_envelope(request, payload)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/refresh", summary="Refresh Deployment Center dashboard")
async def deployment_refresh(
    request: Request,
    _viewer: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    payload = await DeploymentCenterService(db_session, app_settings).get_dashboard()
    return build_envelope(request, DeploymentCenterDashboard(**payload).model_dump())
