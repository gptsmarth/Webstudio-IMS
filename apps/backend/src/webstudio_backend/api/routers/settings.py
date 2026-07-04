"""System settings API endpoints."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import (
    BackupManageDep,
    BackupOrRestoreViewDep,
    BackupViewDep,
    RestoreExecuteDep,
    RestoreViewDep,
    SettingsReadDep,
    SettingsWriteDep,
)
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.settings import (
    AIProviderTestRequest,
    AIProviderTestResponse,
    BackupAdminDashboard,
    BackupCreateRequest,
    BackupCreateResponse,
    BackupDetailEntry,
    BackupHistoryEntry,
    BackupImportResponse,
    BackupPreviewRequest,
    BackupPreviewResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    BackupRollbackRequest,
    BackupSettingsUpdate,
    BackupValidateRequest,
    BackupValidateResponse,
    BackupVerifyResponse,
    CompatibilityReport,
    ExcelSettings,
    GeneralSettings,
    IntegrationsSettingsUpdate,
    InventorySettings,
    MobileBackupStatusResponse,
    NotificationSettings,
    RecoveryCenterDashboard,
    RecoveryFailureAnalysis,
    RecoveryHealthIssue,
    RecoveryReportsResponse,
    RecoveryValidationCheck,
    RecoveryValidationResponse,
    RestoreHistoryEntry,
    SalesSettings,
    SecuritySettings,
    TallySettingsGroup,
    VerificationCheckEntry,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.permissions import user_has_permission
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.backup_run_filters import BackupHistoryFilters
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.services.ai.enrichment_service import ProductEnrichmentService
from webstudio_backend.services.backup_admin_service import BackupAdminService
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.backup_production_validation_service import (
    BackupProductionValidationService,
)
from webstudio_backend.services.recovery_service import RecoveryService
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


async def _backup_admin(
    db_session: AsyncSession,
    app_settings: Settings,
) -> BackupAdminService:
    service = SettingsService(db_session, app_settings)
    backup_dir = await service.get_backup_folder_path()
    return BackupAdminService(db_session, app_settings, backup_dir=backup_dir)


async def _restore_engine(
    db_session: AsyncSession,
    app_settings: Settings,
) -> RestoreEngine:
    service = SettingsService(db_session, app_settings)
    backup_dir = await service.get_backup_folder_path()
    return RestoreEngine(db_session, app_settings, backup_dir=backup_dir)


async def _recovery(
    db_session: AsyncSession,
    app_settings: Settings,
) -> RecoveryService:
    service = SettingsService(db_session, app_settings)
    backup_dir = await service.get_backup_folder_path()
    return RecoveryService(db_session, app_settings, backup_dir=backup_dir)


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return Envelope(
        data=data,
        meta=meta,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _page_meta(page: int, page_size: int, total_items: int, total_pages: int) -> ResponseMeta:
    return build_page_meta(page, page_size, total_items, total_pages)


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
    try:
        updated = await SettingsService(db_session, app_settings).update_tally(
            body,
            actor_id=current.user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
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


@router.post("/integrations/ai/test")
async def test_ai_provider_connection(
    request: Request,
    body: AIProviderTestRequest,
    current: SettingsWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    del current
    provider = body.provider.strip().lower()
    if provider not in {"gemini", "openai", "groq", "openrouter", "mock"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported AI provider."
        )
    result = await ProductEnrichmentService(db_session, app_settings).test_provider(provider)  # type: ignore[arg-type]
    response = AIProviderTestResponse(
        provider=result.provider,
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
    )
    return _envelope(request, response.model_dump())


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


@router.patch("/backup")
async def update_backup_settings(
    request: Request,
    body: BackupSettingsUpdate,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    updated = await SettingsService(db_session, app_settings).update_backup(
        body,
        actor_id=current.user.id,
    )
    return _envelope(request, updated.model_dump())


@router.post("/backups")
async def create_backup(
    request: Request,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    body: BackupCreateRequest | None = None,
) -> dict:
    payload = body or BackupCreateRequest()
    service = SettingsService(db_session, app_settings)
    backup_dir = await service.get_backup_folder_path()
    storage_backend = await service.get_backup_storage_backend()
    try:
        result = await BackupEngine(db_session, app_settings, backup_dir=backup_dir).create_backup(
            backup_type=payload.backup_type,
            trigger_type=payload.trigger_type,
            creator_user_id=current.user.id,
            creator_display_name=current.user.display_name or current.user.username,
            storage_backend=storage_backend,
        )
    except RepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return _envelope(
        request,
        BackupCreateResponse(
            id=result.id,
            filename=result.filename,
            size_bytes=result.size_bytes,
            created_at=result.created_at,
            backup_type=result.backup_type,
            trigger_type=result.trigger_type,
            verification_status=result.verification_status,
            duration_ms=result.duration_ms,
            checksum_sha256=result.checksum_sha256,
            warnings=result.warnings,
            errors=result.errors,
        ).model_dump(),
    )


@router.post("/backups/validate")
async def validate_backup(
    request: Request,
    body: BackupValidateRequest,
    current: RestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    try:
        engine = await _restore_engine(db_session, app_settings)
        result = await engine.validate_backup(
            body.filename,
            source=body.source,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupValidateResponse(
            valid=result.valid,
            filename=result.filename,
            source=result.source,
            checksum_valid=result.checksum_valid,
            integrity_valid=result.integrity_valid,
            corruption_detected=result.corruption_detected,
            app_version=result.app_version,
            schema_version=result.schema_version,
            backup_version=result.backup_version,
            current_app_version=result.current_app_version,
            current_schema_version=result.current_schema_version,
            compatibility=result.compatibility,
            backup_type=result.backup_type,
            trigger_type=result.trigger_type,
            timestamp=result.timestamp,
            size_bytes=result.size_bytes,
            company_name=result.company_name,
            created_by=result.created_by,
            database_size_bytes=result.database_size_bytes,
            inventory_count=result.inventory_count,
            sales_count=result.sales_count,
            users_count=result.users_count,
            audit_log_count=result.audit_log_count,
            restore_allowed=result.restore_allowed,
            migration_required=result.migration_required,
            compatibility_report=CompatibilityReport(**result.compatibility_report),
            backup_format_id=result.backup_format_id,
            backup_format_label=result.backup_format_label,
            warnings=result.warnings,
            errors=result.errors,
        ).model_dump(),
    )


@router.post("/backups/preview")
async def preview_restore(
    request: Request,
    body: BackupPreviewRequest,
    current: RestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    try:
        engine = await _restore_engine(db_session, app_settings)
        result = await engine.preview_restore(
            body.filename,
            restore_scope=body.restore_scope,
            source=body.source,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupPreviewResponse(
            filename=result.filename,
            source=result.source,
            restore_scope=result.restore_scope,
            scope_implemented=result.scope_implemented,
            backup_type=result.backup_type,
            trigger_type=result.trigger_type,
            timestamp=result.timestamp,
            contents=result.contents,
            affected_areas=result.affected_areas,
            warnings=result.warnings,
            emergency_backup_recommended=result.emergency_backup_recommended,
            company_name=result.company_name,
            created_by=result.created_by,
            app_version=result.app_version,
            backup_version=result.backup_version,
            schema_version=result.schema_version,
            inventory_count=result.inventory_count,
            sales_count=result.sales_count,
            users_count=result.users_count,
            database_size_bytes=result.database_size_bytes,
            compressed_size_bytes=result.compressed_size_bytes,
            checksum_valid=result.checksum_valid,
            schema_compatibility=result.schema_compatibility,
            restore_allowed=result.restore_allowed,
            migration_required=result.migration_required,
            compatibility_summary=result.compatibility_summary,
            backup_format_id=result.backup_format_id,
            backup_format_label=result.backup_format_label,
        ).model_dump(),
    )


@router.post("/backups/import")
async def import_backup(
    request: Request,
    current: RestoreExecuteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    file: UploadFile = File(...),
) -> dict:
    _ = current
    content = await file.read()
    try:
        engine = await _restore_engine(db_session, app_settings)
        imported = engine.import_backup_file(
            content,
            file.filename or "import.tar.gz",
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupImportResponse(
            filename=imported.filename,
            size_bytes=len(content),
            source="imported",
            backup_format_id=imported.backup_format_id,
            backup_format_label=imported.backup_format_label,
        ).model_dump(),
    )


@router.post("/backups/restore")
async def restore_backup(
    request: Request,
    body: BackupRestoreRequest,
    current: RestoreExecuteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        engine = await _restore_engine(db_session, app_settings)
        result = await engine.execute_restore(
            filename=body.filename,
            restore_scope=body.restore_scope,
            source=body.source,
            create_emergency_backup=body.create_emergency_backup,
            confirmed=body.confirmed,
            actor_user_id=current.user.id,
            actor_display_name=current.user.display_name or current.user.username,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupRestoreResponse(
            success=result.success,
            filename=result.filename,
            restore_scope=result.restore_scope,
            emergency_backup_filename=result.emergency_backup_filename,
            rollback_available=result.rollback_available,
            rollback_recommended=result.rollback_recommended,
            verification_status=result.verification_status,
            duration_ms=result.duration_ms,
            warnings=result.warnings,
            errors=result.errors,
            restart_required=result.restart_required,
            verification_checks=[
                VerificationCheckEntry(**check) for check in result.verification_checks
            ],
        ).model_dump(),
    )


@router.post("/backups/rollback")
async def rollback_backup(
    request: Request,
    body: BackupRollbackRequest,
    current: RestoreExecuteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        engine = await _restore_engine(db_session, app_settings)
        result = await engine.rollback_restore(
            emergency_backup_filename=body.emergency_backup_filename,
            confirmed=body.confirmed,
            actor_user_id=current.user.id,
            actor_display_name=current.user.display_name or current.user.username,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(
        request,
        BackupRestoreResponse(
            success=result.success,
            filename=result.filename,
            restore_scope=result.restore_scope,
            emergency_backup_filename=result.emergency_backup_filename,
            rollback_available=result.rollback_available,
            rollback_recommended=result.rollback_recommended,
            verification_status=result.verification_status,
            duration_ms=result.duration_ms,
            warnings=result.warnings,
            errors=result.errors,
            restart_required=result.restart_required,
            verification_checks=[
                VerificationCheckEntry(**check) for check in result.verification_checks
            ],
        ).model_dump(),
    )


@router.get(
    "/backups/production-validation",
    summary="Run M14D production backup and disaster recovery validation",
)
async def backup_production_validation(
    request: Request,
    current: BackupOrRestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    settings_service = SettingsService(db_session, app_settings)
    backup_dir = await settings_service.get_backup_folder_path()
    service = BackupProductionValidationService(db_session, app_settings, backup_dir=backup_dir)
    payload = await service.build_production_report()
    return _envelope(request, payload)


@router.get("/recovery/center")
async def recovery_center(
    request: Request,
    current: BackupOrRestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    _, database_health = await _health_snapshot(db_session)
    center = await _recovery(db_session, app_settings)
    dashboard = await center.get_center(database_health=database_health)
    center_data = asdict(dashboard)
    center_data["health_issues"] = [
        RecoveryHealthIssue(**asdict(issue)) for issue in dashboard.health_issues
    ]
    payload = RecoveryCenterDashboard(**center_data)
    return _envelope(request, payload.model_dump())


@router.post("/recovery/validate")
async def recovery_validate(
    request: Request,
    current: RestoreExecuteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    recovery = await _recovery(db_session, app_settings)
    result = await recovery.run_validation(
        actor_user_id=current.user.id,
        actor_display_name=current.user.display_name,
    )
    return _envelope(
        request,
        RecoveryValidationResponse(
            overall_status=result.overall_status,
            checks=[RecoveryValidationCheck(**asdict(check)) for check in result.checks],
        ).model_dump(),
    )


@router.get("/recovery/health-checks")
async def recovery_health_checks(
    request: Request,
    current: BackupOrRestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    _, database_health = await _health_snapshot(db_session)
    recovery = await _recovery(db_session, app_settings)
    issues = await recovery.collect_health_checks(database_health=database_health)
    items = [RecoveryHealthIssue(**asdict(issue)).model_dump() for issue in issues]
    return _envelope(request, items)


@router.get("/recovery/reports")
async def recovery_reports(
    request: Request,
    current: RestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    recovery = await _recovery(db_session, app_settings)
    reports = await recovery.get_reports()
    return _envelope(
        request,
        RecoveryReportsResponse(
            recovery_history=[RestoreHistoryEntry(**row) for row in reports.recovery_history],
            backup_success_rate=reports.backup_success_rate,
            total_backups=reports.total_backups,
            successful_backups=reports.successful_backups,
            failed_backups=reports.failed_backups,
            failure_analysis=[RecoveryFailureAnalysis(**row) for row in reports.failure_analysis],
            export_supported=reports.export_supported,
        ).model_dump(),
    )


@router.get("/backups/admin/dashboard")
async def backup_admin_dashboard(
    request: Request,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    _, database_health = await _health_snapshot(db_session)
    admin = await _backup_admin(db_session, app_settings)
    dashboard = await admin.get_dashboard(database_health=database_health)
    return _envelope(request, BackupAdminDashboard(**asdict(dashboard)).model_dump())


@router.get("/backups/admin/history")
async def backup_admin_history(
    request: Request,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    backup_type: str | None = None,
    trigger_type: str | None = None,
    creator: str | None = None,
    status: str | None = None,
    include_archived: bool = True,
) -> dict:
    _ = current
    admin = await _backup_admin(db_session, app_settings)
    filters = BackupHistoryFilters(
        date_from=date_from,
        date_to=date_to,
        backup_type=backup_type,
        trigger_type=trigger_type,
        creator=creator,
        status=status,
        include_archived=include_archived,
    )
    result = await admin.list_history(filters, PageParams(page=page, page_size=page_size))
    items = [BackupHistoryEntry(**row).model_dump() for row in result.items]
    meta = _page_meta(result.page, result.page_size, result.total_items, result.total_pages)
    return _envelope(request, items, meta)


@router.get("/backups/admin/history/export")
async def backup_admin_history_export(
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    backup_type: str | None = None,
    trigger_type: str | None = None,
    creator: str | None = None,
    status: str | None = None,
    include_archived: bool = True,
) -> Response:
    _ = current
    admin = await _backup_admin(db_session, app_settings)
    filters = BackupHistoryFilters(
        date_from=date_from,
        date_to=date_to,
        backup_type=backup_type,
        trigger_type=trigger_type,
        creator=creator,
        status=status,
        include_archived=include_archived,
    )
    content, media_type, filename = await admin.export_history(filters, export_format=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/backups/{filename}/details")
async def backup_details(
    request: Request,
    filename: str,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    try:
        admin = await _backup_admin(db_session, app_settings)
        detail = await admin.get_details(filename)
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, BackupDetailEntry(**detail).model_dump())


@router.get("/backups/{filename}/download")
async def backup_download(
    filename: str,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> Response:
    _ = current
    try:
        admin = await _backup_admin(db_session, app_settings)
        path = admin.resolve_download_path(filename)
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    content = path.read_bytes()
    media_type = "application/gzip" if filename.endswith(".tar.gz") else "application/sql"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/backups/{filename}/verify")
async def backup_verify(
    request: Request,
    filename: str,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        admin = await _backup_admin(db_session, app_settings)
        result = await admin.verify_backup(
            filename,
            actor_user_id=current.user.id,
            actor_display_name=current.user.display_name or current.user.username,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(request, BackupVerifyResponse(**result).model_dump())


@router.post("/backups/{filename}/archive")
async def backup_archive(
    request: Request,
    filename: str,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        admin = await _backup_admin(db_session, app_settings)
        result = await admin.archive_backup(
            filename,
            actor_user_id=current.user.id,
            actor_display_name=current.user.display_name or current.user.username,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(request, BackupHistoryEntry(**result).model_dump())


@router.delete("/backups/{filename}")
async def backup_delete(
    request: Request,
    filename: str,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    try:
        admin = await _backup_admin(db_session, app_settings)
        result = await admin.delete_backup(
            filename,
            actor_user_id=current.user.id,
            actor_display_name=current.user.display_name or current.user.username,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _envelope(request, result)


@router.get("/backups/mobile/status")
async def mobile_backup_status(
    request: Request,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _, database_health = await _health_snapshot(db_session)
    admin = await _backup_admin(db_session, app_settings)
    dashboard = await admin.get_dashboard(database_health=database_health)
    settings = SettingsService(db_session, app_settings)
    last_backup = (await settings.get_workspace()).backup.last_backup_at
    granted = set(current.permissions)
    return _envelope(
        request,
        MobileBackupStatusResponse(
            health_status=dashboard.storage_health,
            backup_status=dashboard.storage_health,
            last_backup_at=last_backup,
            total_backups=dashboard.total_backup_count,
            failed_backups=dashboard.failed_backup_count,
            storage_free_bytes=dashboard.storage_free_bytes,
            storage_total_bytes=dashboard.storage_total_bytes,
            can_trigger_backup=user_has_permission(granted, "backup:manage"),
            restore_history_available=user_has_permission(granted, "restore:view"),
        ).model_dump(),
    )


@router.get("/backups/mobile/history")
async def mobile_backup_history(
    request: Request,
    current: BackupViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    _ = current
    admin = await _backup_admin(db_session, app_settings)
    result = await admin.list_history(
        BackupHistoryFilters(), PageParams(page=page, page_size=page_size)
    )
    items = [BackupHistoryEntry(**row).model_dump() for row in result.items]
    meta = _page_meta(result.page, result.page_size, result.total_items, result.total_pages)
    return _envelope(request, items, meta)


@router.post("/backups/mobile")
async def mobile_trigger_backup(
    request: Request,
    current: BackupManageDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    service = SettingsService(db_session, app_settings)
    backup_dir = await service.get_backup_folder_path()
    engine = BackupEngine(db_session, app_settings, backup_dir=backup_dir)
    result = await engine.create_backup(
        backup_type="full",
        trigger_type="manual",
        creator_user_id=current.user.id,
        creator_display_name=current.user.display_name or current.user.username,
    )
    return _envelope(
        request,
        BackupCreateResponse(
            filename=result.filename,
            size_bytes=result.size_bytes,
            created_at=result.created_at,
            backup_type=result.backup_type,
            trigger_type=result.trigger_type,
            verification_status=result.verification_status,
            duration_ms=result.duration_ms,
            checksum_sha256=result.checksum_sha256,
            warnings=result.warnings,
            errors=result.errors,
        ).model_dump(),
    )


@router.get("/backups/mobile/restore-history")
async def mobile_restore_history(
    request: Request,
    current: RestoreViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings: Settings = AppSettingsDep,
) -> dict:
    _ = current
    recovery = await _recovery(db_session, app_settings)
    reports = await recovery.get_reports()
    items = [RestoreHistoryEntry(**row).model_dump() for row in reports.recovery_history]
    return _envelope(request, items)
