"""System settings API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import SettingsReadDep, SettingsWriteDep
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.api.schemas.settings import (
    BackupCreateResponse,
    BackupRestoreRequest,
    ExcelSettings,
    GeneralSettings,
    IntegrationsSettings,
    IntegrationsSettingsUpdate,
    InventorySettings,
    NotificationSettings,
    SalesSettings,
    SecuritySettings,
    TallySettingsGroup,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.services.backup_service import BackupService
from webstudio_backend.services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


async def _health_snapshot(db_session: AsyncSession) -> tuple[str, str]:
    api_health = "ok"
    database_health = "ok"
    try:
        await db_session.execute(text("SELECT 1"))
    except Exception:
        database_health = "failed"
    return api_health, database_health


@router.get("")
async def get_settings_workspace(
    request: Request,
    current: SettingsReadDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    api_health, database_health = await _health_snapshot(db_session)
    workspace = await SettingsService(db_session, app_settings).get_workspace(
        api_health=api_health,
        database_health=database_health,
    )
    return _envelope(request, workspace.model_dump())


@router.patch("/general")
async def update_general_settings(
    request: Request,
    body: GeneralSettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_general(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/security")
async def update_security_settings(
    request: Request,
    body: SecuritySettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_security(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/inventory")
async def update_inventory_settings(
    request: Request,
    body: InventorySettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_inventory(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/sales")
async def update_sales_settings(
    request: Request,
    body: SalesSettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_sales(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/tally")
async def update_tally_settings(
    request: Request,
    body: TallySettingsGroup,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_tally(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/integrations")
async def update_integrations_settings(
    request: Request,
    body: IntegrationsSettingsUpdate,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_integrations(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/excel")
async def update_excel_settings(
    request: Request,
    body: ExcelSettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_excel(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.patch("/notifications")
async def update_notification_settings(
    request: Request,
    body: NotificationSettings,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_notifications(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.post("/backups")
async def create_backup(
    request: Request,
    current: SettingsWriteDep,
) -> dict:
    _ = current
    try:
        entry = BackupService().create_backup()
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupCreateResponse(
            filename=entry.filename,
            size_bytes=entry.size_bytes,
            created_at=entry.created_at,
        ).model_dump(),
    )


@router.post("/backups/restore")
async def restore_backup(
    request: Request,
    body: BackupRestoreRequest,
    current: SettingsWriteDep,
) -> dict:
    _ = current
    try:
        BackupService().restore_backup(body.filename)
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(request, {"success": True, "filename": body.filename})
