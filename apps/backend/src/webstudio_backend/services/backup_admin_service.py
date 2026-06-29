"""Backup administration — history, storage, retention, and lifecycle actions."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.repositories.backup_run_filters import BackupHistoryFilters
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_engine import LEGACY_SQL_PATTERN, BackupEngine
from webstudio_backend.services.backup_history_export import (
    backup_history_export_filename,
    build_backup_history_pdf,
    build_backup_history_xlsx,
)
from webstudio_backend.services.backup_schedule import (
    STORAGE_CRITICAL_BYTES,
    STORAGE_WARNING_BYTES,
    backup_health_status,
    estimate_remaining_backups,
    resolve_retention_limit,
)
from webstudio_backend.services.restore_engine import RestoreEngine


@dataclass(frozen=True, slots=True)
class BackupAdminDashboard:
    storage_health: str
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    backup_folder: str
    backup_folder_used_bytes: int
    retention_policy: str
    retention_count: int
    oldest_backup_at: str | None
    newest_backup_at: str | None
    failed_backup_count: int
    warning_count: int
    archived_count: int
    total_backup_count: int
    estimated_remaining_backups: int | None = None
    retention_used: int = 0
    warning_threshold_bytes: int = 0
    critical_threshold_bytes: int = 0


class BackupAdminService:
    def __init__(
        self,
        session: AsyncSession,
        app_settings: Settings,
        *,
        backup_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._settings = app_settings
        self._runs = BackupRunRepository(session)
        self._settings_repo = SystemSettingRepository(session)
        self._recorder = AuditRecorder(session)
        self._engine = BackupEngine(session, app_settings, backup_dir=backup_dir)
        self._backup_root = self._engine._backup_root  # noqa: SLF001

    async def get_dashboard(self, *, database_health: str = "ok") -> BackupAdminDashboard:
        disk = shutil.disk_usage(self._backup_root.anchor or "/")
        folder_used = self._folder_size_bytes(self._backup_root)
        summary = await self._runs.count_summary()
        oldest, newest = await self._runs.oldest_and_newest()
        policy = await self._settings_repo.get_string("backup_retention_policy") or "last_30"
        retention_count = await self._settings_repo.get_int("backup_retention_count", default=30)
        recent = await self._runs.list_recent(limit=1)
        last_verification = recent[0].verification_status if recent else None
        storage_health = backup_health_status(
            database_health=database_health,
            last_verification_status=last_verification,
            storage_free_bytes=disk.free,
        )
        retention_limit = resolve_retention_limit(policy, retention_count)
        average_backup = int(recent[0].size_bytes) if recent else 0
        return BackupAdminDashboard(
            storage_health=storage_health,
            storage_total_bytes=disk.total,
            storage_used_bytes=disk.used,
            storage_free_bytes=disk.free,
            backup_folder=str(self._backup_root),
            backup_folder_used_bytes=folder_used,
            retention_policy=policy,
            retention_count=retention_count,
            oldest_backup_at=oldest.isoformat() if oldest else None,
            newest_backup_at=newest.isoformat() if newest else None,
            failed_backup_count=summary["failed"],
            warning_count=summary["warnings"],
            archived_count=summary["archived"],
            total_backup_count=summary["total"],
            estimated_remaining_backups=estimate_remaining_backups(
                storage_free_bytes=disk.free,
                average_backup_bytes=average_backup,
                retention_count=retention_limit,
            ),
            retention_used=summary["total"],
            warning_threshold_bytes=STORAGE_WARNING_BYTES,
            critical_threshold_bytes=STORAGE_CRITICAL_BYTES,
        )

    async def list_history(
        self,
        filters: BackupHistoryFilters,
        page_params: PageParams,
    ) -> PageResult[dict[str, Any]]:
        page = await self._runs.search(filters, page_params)
        items = [self._engine._run_to_dict(run) for run in page.items]  # noqa: SLF001
        unfiltered = (
            page.page == 1
            and not filters.backup_type
            and not filters.status
            and not filters.creator
        )
        if unfiltered:
            legacy = [
                self._engine._legacy_entry(path)  # noqa: SLF001
                for path in self._engine._legacy_sql_files()[:5]
            ]
            legacy_names = {entry["filename"] for entry in legacy}
            items = legacy + [item for item in items if item["filename"] not in legacy_names]
        return PageResult(
            items=items,
            total_items=page.total_items,
            page=page.page,
            page_size=page.page_size,
        )

    async def get_details(self, filename: str) -> dict[str, Any]:
        run = await self._runs.get_by_filename(filename)
        if run is not None:
            detail = self._engine._run_to_dict(run)  # noqa: SLF001
            manifest = json.loads(run.manifest_json or "{}")
            detail["manifest"] = manifest
            detail["archive_path"] = run.archive_path
            return detail
        path = self._backup_root / filename
        if LEGACY_SQL_PATTERN.match(filename) and path.is_file():
            entry = self._engine._legacy_entry(path)  # noqa: SLF001
            entry["manifest"] = {}
            entry["archive_path"] = str(path)
            return entry
        raise RepositoryError(f"Backup not found: {filename}")

    def resolve_download_path(self, filename: str) -> Path:
        path = self._backup_root / filename
        if not path.is_file():
            raise RepositoryError(f"Backup file not found: {filename}")
        return path

    async def verify_backup(
        self,
        filename: str,
        *,
        actor_user_id: int | None,
        actor_display_name: str | None,
    ) -> dict[str, Any]:
        from webstudio_backend.services.backup_alert_service import BackupAlertService
        from webstudio_backend.services.backup_verification import verify_backup_integrity

        restore = RestoreEngine(self._session, self._settings, backup_dir=self._backup_root)
        source = "imported" if filename.startswith("webstudio-import-") else "local"
        archive_path = self._backup_root / filename
        run = await self._runs.get_by_filename(filename)
        manifest = (
            json.loads(run.manifest_json or "{}")
            if run and run.manifest_json
            else self._engine.read_manifest_from_archive(archive_path)
        )
        integrity = await verify_backup_integrity(
            filename=filename,
            archive_path=archive_path,
            manifest=manifest,
            stored_checksum=run.checksum_sha256 if run else None,
            checksum_file_fn=self._engine._checksum_file,  # noqa: SLF001
        )
        if run is not None:
            run.verification_status = integrity.verification_status
            run.warnings_json = json.dumps(integrity.warnings)
            run.errors_json = json.dumps(integrity.errors)
            await self._session.flush()
        await self._audit_admin_action(
            filename=filename,
            action="verify",
            actor_user_id=actor_user_id,
            actor_display_name=actor_display_name,
            success=integrity.valid,
        )
        if not integrity.valid:
            await BackupAlertService(self._session).notify_backup_verification_failed(
                filename=filename,
                detail="; ".join(integrity.errors) or integrity.overall_health,
            )
        await self._session.commit()
        validation = await restore.validate_backup(filename, source=source)
        return {
            "filename": filename,
            "valid": integrity.valid,
            "checksum_valid": integrity.checksum_valid,
            "integrity_valid": integrity.integrity_valid,
            "compression_valid": integrity.compression_valid,
            "manifest_valid": integrity.manifest_valid,
            "corruption_detected": integrity.corruption_detected,
            "verification_status": integrity.verification_status,
            "overall_health": integrity.overall_health,
            "warnings": integrity.warnings + validation.warnings,
            "errors": integrity.errors + validation.errors,
            "checks": [
                {"key": c.key, "name": c.name, "status": c.status, "message": c.message}
                for c in integrity.checks
            ],
        }

    async def archive_backup(
        self,
        filename: str,
        *,
        actor_user_id: int | None,
        actor_display_name: str | None,
    ) -> dict[str, Any]:
        run = await self._runs.get_by_filename(filename)
        if run is None:
            raise RepositoryError(f"Backup not found: {filename}")
        await self._runs.mark_archived(run)
        await self._audit_admin_action(
            filename=filename,
            action="archive",
            actor_user_id=actor_user_id,
            actor_display_name=actor_display_name,
            success=True,
        )
        await self._session.commit()
        return self._engine._run_to_dict(run)  # noqa: SLF001

    async def delete_backup(
        self,
        filename: str,
        *,
        actor_user_id: int | None,
        actor_display_name: str | None,
    ) -> dict[str, str]:
        run = await self._runs.get_by_filename(filename)
        path = self._backup_root / filename
        if run is not None:
            file_path = Path(run.archive_path)
            if file_path.is_file():
                file_path.unlink(missing_ok=True)
            await self._runs.delete_run(run)
        elif path.is_file():
            path.unlink(missing_ok=True)
        else:
            raise RepositoryError(f"Backup not found: {filename}")
        await self._audit_admin_action(
            filename=filename,
            action="delete",
            actor_user_id=actor_user_id,
            actor_display_name=actor_display_name,
            success=True,
        )
        await self._session.commit()
        return {"filename": filename, "deleted": "true"}

    async def export_history(
        self,
        filters: BackupHistoryFilters,
        *,
        export_format: str,
    ) -> tuple[bytes, str, str]:
        page = await self.list_history(filters, PageParams(page=1, page_size=100))
        rows = page.items
        title = "WEBSTUDIO IMS — Backup History"
        if export_format == "xlsx":
            content = build_backup_history_xlsx(title, rows)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content = build_backup_history_pdf(title, rows)
            media_type = "application/pdf"
        filename = backup_history_export_filename(export_format)
        return content, media_type, filename

    @staticmethod
    def _folder_size_bytes(folder: Path) -> int:
        if not folder.exists():
            return 0
        total = 0
        for path in folder.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    async def _audit_admin_action(
        self,
        *,
        filename: str,
        action: str,
        actor_user_id: int | None,
        actor_display_name: str | None,
        success: bool,
    ) -> None:
        actor = AuditActor(
            user_id=actor_user_id,
            display_name=actor_display_name or "System",
            role="main_admin" if actor_user_id else "system",
        )
        await self._recorder.record_backup_operation(
            filename=filename,
            backup_type=action,
            trigger_type="admin",
            verification_status="success" if success else "failed",
            size_bytes=0,
            actor=actor,
            success=success,
        )
