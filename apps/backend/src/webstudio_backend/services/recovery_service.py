"""Disaster recovery — health checks, validation, and reporting."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.backup_run import BackupRun
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.restore_run import RestoreRun
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.restore_run_repository import (
    RestoreRunRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.backup_schedule import (
    LOW_STORAGE_BYTES,
    OLD_BACKUP_THRESHOLD_DAYS,
    STORAGE_CRITICAL_BYTES,
    STORAGE_WARNING_BYTES,
    backup_health_status,
    compute_readiness_score,
    compute_recovery_readiness,
    compute_system_health,
    estimate_remaining_backups,
    resolve_retention_limit,
)
from webstudio_backend.services.settings_registry import SETTING_DEFAULTS


@dataclass(frozen=True, slots=True)
class HealthIssue:
    code: str
    severity: str
    title: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    key: str
    name: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class RecoveryCenter:
    system_health: str
    database_status: str
    backup_status: str
    storage_status: str
    recovery_readiness: str
    storage_free_bytes: int
    storage_total_bytes: int
    storage_used_bytes: int
    backup_folder: str
    last_backup_at: str | None
    last_restore_at: str | None
    failed_backup_count: int
    health_issues: list[HealthIssue]
    readiness_score: dict[str, int | str]
    storage_monitoring: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RecoveryValidation:
    overall_status: str
    checks: list[ValidationCheck]


@dataclass(frozen=True, slots=True)
class RecoveryReports:
    recovery_history: list[dict[str, Any]]
    backup_success_rate: float
    total_backups: int
    successful_backups: int
    failed_backups: int
    failure_analysis: list[dict[str, Any]]
    export_supported: bool = False


class RecoveryService:
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
        self._restores = RestoreRunRepository(session)
        self._settings_repo = SystemSettingRepository(session)
        self._recorder = AuditRecorder(session)
        self._engine = BackupEngine(session, app_settings, backup_dir=backup_dir)
        self._backup_root = self._engine._backup_root  # noqa: SLF001

    async def get_center(self, *, database_health: str) -> RecoveryCenter:
        disk = shutil.disk_usage(self._backup_root.anchor or "/")
        summary = await self._runs.count_summary()
        recent = await self._runs.list_recent(limit=1)
        last_verification = recent[0].verification_status if recent else None
        backup_status = backup_health_status(
            database_health=database_health,
            last_verification_status=last_verification,
            storage_free_bytes=disk.free,
        )
        issues = await self.collect_health_checks(database_health=database_health)
        last_backup_raw = await self._settings_repo.get_string("last_backup_at")
        restore_runs = await self._restores.list_recent(limit=1)
        last_restore_at = (
            restore_runs[0].completed_at.isoformat()
            if restore_runs and restore_runs[0].completed_at
            else None
        )
        has_recent_backup = self._has_recent_backup(last_backup_raw)
        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        system_health = compute_system_health(
            database_health=database_health,
            backup_health=backup_status,
            open_critical_issues=critical_count,
            open_warning_issues=warning_count,
        )
        storage_status = "healthy" if disk.free >= LOW_STORAGE_BYTES else "warning"
        if disk.free < LOW_STORAGE_BYTES // 4:
            storage_status = "critical"
        recovery_readiness = compute_recovery_readiness(
            database_health=database_health,
            backup_health=backup_status,
            has_recent_backup=has_recent_backup,
            failed_backup_count=summary["failed"],
            open_health_issues=len(issues),
        )
        backup_age_days = self._backup_age_days(last_backup_raw)
        readiness_score = compute_readiness_score(
            database_health=database_health,
            backup_health=backup_status,
            storage_status=storage_status,
            latest_backup_age_days=backup_age_days,
            latest_verification_status=last_verification,
            recovery_readiness=recovery_readiness,
        )
        policy = await self._settings_repo.get_string("backup_retention_policy") or "last_30"
        retention_count = await self._settings_repo.get_int("backup_retention_count", default=30)
        retention_limit = resolve_retention_limit(policy, retention_count)
        average_backup = int(recent[0].size_bytes) if recent else 0
        folder_used = self._folder_size_bytes(self._backup_root)
        storage_monitoring = {
            "storage_total_bytes": disk.total,
            "storage_used_bytes": disk.used,
            "storage_free_bytes": disk.free,
            "backup_folder": str(self._backup_root),
            "backup_folder_used_bytes": folder_used,
            "estimated_remaining_backups": estimate_remaining_backups(
                storage_free_bytes=disk.free,
                average_backup_bytes=average_backup,
                retention_count=retention_limit,
            ),
            "retention_policy": policy,
            "retention_count": retention_limit,
            "retention_used": summary["total"],
            "warning_threshold_bytes": STORAGE_WARNING_BYTES,
            "critical_threshold_bytes": STORAGE_CRITICAL_BYTES,
        }
        return RecoveryCenter(
            system_health=system_health,
            database_status="ok" if database_health == "ok" else "failed",
            backup_status=backup_status,
            storage_status=storage_status,
            recovery_readiness=recovery_readiness,
            storage_free_bytes=disk.free,
            storage_total_bytes=disk.total,
            storage_used_bytes=disk.used,
            backup_folder=str(self._backup_root),
            last_backup_at=last_backup_raw or None,
            last_restore_at=last_restore_at,
            failed_backup_count=summary["failed"],
            health_issues=issues,
            readiness_score=readiness_score,
            storage_monitoring=storage_monitoring,
        )

    async def collect_health_checks(self, *, database_health: str) -> list[HealthIssue]:
        issues: list[HealthIssue] = []
        disk = shutil.disk_usage(self._backup_root.anchor or "/")
        summary = await self._runs.count_summary()
        recent_runs = await self._runs.list_recent(limit=10)
        last_backup_raw = await self._settings_repo.get_string("last_backup_at")

        if database_health != "ok":
            issues.append(
                HealthIssue(
                    code="database_failure",
                    severity="critical",
                    title="Database failure",
                    message="Database connectivity check failed. Recovery may not be possible.",
                ),
            )

        if summary["total"] == 0:
            issues.append(
                HealthIssue(
                    code="missing_backup",
                    severity="critical",
                    title="No backups found",
                    message="No enterprise backups exist. Run a manual backup immediately.",
                ),
            )
        elif not self._has_recent_backup(last_backup_raw):
            issues.append(
                HealthIssue(
                    code="old_backup",
                    severity="warning",
                    title="Backup is outdated",
                    message=(
                        f"No backup within the last {OLD_BACKUP_THRESHOLD_DAYS} days. "
                        "Schedule or run a fresh backup."
                    ),
                ),
            )

        if summary["failed"] > 0:
            issues.append(
                HealthIssue(
                    code="backup_failure",
                    severity="warning",
                    title="Failed backups detected",
                    message=f"{summary['failed']} backup run(s) failed. Review backup history.",
                ),
            )

        if disk.free < LOW_STORAGE_BYTES:
            issues.append(
                HealthIssue(
                    code="low_storage",
                    severity="warning",
                    title="Low storage",
                    message="Backup volume is running low on free space.",
                ),
            )

        for run in recent_runs:
            if run.verification_status == "failed":
                issues.append(
                    HealthIssue(
                        code="corrupted_backup",
                        severity="critical",
                        title="Corrupted backup detected",
                        message=f"Backup '{run.filename}' failed integrity verification.",
                    ),
                )
                break
            archive_path = Path(run.archive_path)
            if not archive_path.is_file():
                issues.append(
                    HealthIssue(
                        code="missing_backup",
                        severity="critical",
                        title="Backup file missing",
                        message=f"Backup record '{run.filename}' is missing from disk.",
                    ),
                )
                break

        return issues

    async def run_validation(
        self,
        *,
        actor_user_id: int | None = None,
        actor_display_name: str | None = None,
    ) -> RecoveryValidation:
        checks: list[ValidationCheck] = []
        checks.append(await self._check_database_integrity())
        checks.append(await self._check_schema_version())
        checks.append(await self._check_missing_files())
        checks.append(await self._check_configuration())
        checks.append(await self._check_permissions())
        checks.append(await self._check_product_images())
        checks.append(await self._check_tally_configuration())
        checks.append(await self._check_application_settings())

        statuses = {check.status for check in checks}
        if "failed" in statuses:
            overall = "failed"
        elif "warning" in statuses:
            overall = "warning"
        else:
            overall = "passed"

        await self._recorder.record_recovery_validation(
            actor=AuditActor(user_id=actor_user_id, display_name=actor_display_name),
            overall_status=overall,
            checks=[asdict(check) for check in checks],
        )
        await self._session.commit()
        return RecoveryValidation(overall_status=overall, checks=checks)

    async def get_reports(self) -> RecoveryReports:
        restore_rows = await self._restores.list_recent(limit=25)
        recovery_history = [self._restore_to_dict(run) for run in restore_rows]

        total = await self._count_backups()
        successful = await self._count_backups(status="completed")
        failed = await self._count_backups(status="failed")
        success_rate = round((successful / total) * 100, 1) if total else 0.0

        failure_rows = await self._session.execute(
            select(BackupRun.verification_status, func.count(BackupRun.id))
            .where(BackupRun.status == "failed")
            .group_by(BackupRun.verification_status),
        )
        failure_analysis = [
            {"reason": row[0] or "unknown", "count": int(row[1])}
            for row in failure_rows.all()
        ]
        if failed and not failure_analysis:
            failure_analysis.append({"reason": "backup_run_failed", "count": failed})

        return RecoveryReports(
            recovery_history=recovery_history,
            backup_success_rate=success_rate,
            total_backups=total,
            successful_backups=successful,
            failed_backups=failed,
            failure_analysis=failure_analysis,
        )

    async def _check_database_integrity(self) -> ValidationCheck:
        try:
            await self._session.execute(text("SELECT 1"))
            size_result = await self._session.execute(
                text("SELECT pg_database_size(current_database())"),
            )
            size_bytes = int(size_result.scalar_one())
            return ValidationCheck(
                key="database_integrity",
                name="Database integrity",
                status="passed",
                message=f"Database is reachable ({size_bytes} bytes).",
            )
        except Exception as exc:
            return ValidationCheck(
                key="database_integrity",
                name="Database integrity",
                status="failed",
                message=f"Database check failed: {exc}",
            )

    async def _check_schema_version(self) -> ValidationCheck:
        version = await self._engine._schema_version()  # noqa: SLF001
        if version == "unknown":
            return ValidationCheck(
                key="schema_version",
                name="Schema version",
                status="warning",
                message="Could not determine current schema version.",
            )
        return ValidationCheck(
            key="schema_version",
            name="Schema version",
            status="passed",
            message=f"Schema version {version} is active.",
        )

    async def _check_missing_files(self) -> ValidationCheck:
        if not self._backup_root.is_dir():
            return ValidationCheck(
                key="missing_files",
                name="Missing files",
                status="failed",
                message=f"Backup folder does not exist: {self._backup_root}",
            )
        recent = await self._runs.list_recent(limit=1)
        if not recent:
            return ValidationCheck(
                key="missing_files",
                name="Missing files",
                status="warning",
                message="No backup archives recorded yet.",
            )
        latest = recent[0]
        archive_path = Path(latest.archive_path)
        if not archive_path.is_file():
            return ValidationCheck(
                key="missing_files",
                name="Missing files",
                status="failed",
                message=f"Latest backup file is missing: {latest.filename}",
            )
        return ValidationCheck(
            key="missing_files",
            name="Missing files",
            status="passed",
            message=f"Latest backup '{latest.filename}' is present on disk.",
        )

    async def _check_configuration(self) -> ValidationCheck:
        folder = await self._settings_repo.get_string("backup_folder") or "backups"
        schedule = await self._settings_repo.get_string("backup_schedule") or "manual"
        return ValidationCheck(
            key="configuration",
            name="Configuration",
            status="passed",
            message=f"Backup folder '{folder}', schedule '{schedule}'.",
        )

    async def _check_permissions(self) -> ValidationCheck:
        try:
            self._backup_root.mkdir(parents=True, exist_ok=True)
            probe = self._backup_root / ".recovery-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return ValidationCheck(
                key="permissions",
                name="Permissions",
                status="passed",
                message="Backup folder is readable and writable.",
            )
        except OSError as exc:
            return ValidationCheck(
                key="permissions",
                name="Permissions",
                status="failed",
                message=f"Backup folder permission check failed: {exc}",
            )

    async def _check_product_images(self) -> ValidationCheck:
        result = await self._session.execute(
            select(func.count(ProductModel.id)).where(ProductModel.product_image_url.is_(None)),
        )
        missing = int(result.scalar_one() or 0)
        total_result = await self._session.execute(select(func.count(ProductModel.id)))
        total = int(total_result.scalar_one() or 0)
        if total == 0:
            return ValidationCheck(
                key="product_images",
                name="Product images",
                status="passed",
                message="No product models configured.",
            )
        if missing == 0:
            return ValidationCheck(
                key="product_images",
                name="Product images",
                status="passed",
                message="All product models have image URLs.",
            )
        return ValidationCheck(
            key="product_images",
            name="Product images",
            status="warning",
            message=f"{missing} of {total} product models are missing image URLs.",
        )

    async def _check_tally_configuration(self) -> ValidationCheck:
        enabled = await self._settings_repo.get_bool("tally_enabled", default=False)
        if not enabled:
            return ValidationCheck(
                key="tally_configuration",
                name="Tally configuration",
                status="passed",
                message="Tally integration is disabled.",
            )
        host = await self._settings_repo.get_string("tally_host") or ""
        company = await self._settings_repo.get_string("tally_company_name") or ""
        if not host.strip() or not company.strip():
            return ValidationCheck(
                key="tally_configuration",
                name="Tally configuration",
                status="warning",
                message="Tally is enabled but host or company name is missing.",
            )
        return ValidationCheck(
            key="tally_configuration",
            name="Tally configuration",
            status="passed",
            message=f"Tally configured for '{company}' at {host}.",
        )

    async def _check_application_settings(self) -> ValidationCheck:
        missing: list[str] = []
        for key in ("company_name", "timezone", "currency"):
            value = await self._settings_repo.get_string(key)
            if not value or not value.strip():
                missing.append(key)
        if missing:
            return ValidationCheck(
                key="application_settings",
                name="Application settings",
                status="warning",
                message=f"Missing values for: {', '.join(missing)}.",
            )
        registry_count = len(SETTING_DEFAULTS)
        return ValidationCheck(
            key="application_settings",
            name="Application settings",
            status="passed",
            message=f"Core settings present ({registry_count} registry keys).",
        )

    async def _count_backups(self, *, status: str | None = None) -> int:
        statement = select(func.count(BackupRun.id))
        if status is not None:
            statement = statement.where(BackupRun.status == status)
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    def _has_recent_backup(self, last_backup_raw: str | None) -> bool:
        return self._backup_age_days(last_backup_raw) is not None and (
            self._backup_age_days(last_backup_raw) or 999
        ) <= OLD_BACKUP_THRESHOLD_DAYS

    def _backup_age_days(self, last_backup_raw: str | None) -> float | None:
        if not last_backup_raw:
            return None
        try:
            last_at = datetime.fromisoformat(last_backup_raw)
        except ValueError:
            return None
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=UTC)
        return (datetime.now(UTC) - last_at).total_seconds() / 86400

    def _folder_size_bytes(self, folder: Path) -> int:
        if not folder.is_dir():
            return 0
        return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())

    def _restore_to_dict(self, run: RestoreRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "filename": run.filename,
            "source": run.source,
            "restore_scope": run.restore_scope,
            "status": run.status,
            "verification_status": run.verification_status,
            "emergency_backup_filename": run.emergency_backup_filename,
            "duration_ms": run.duration_ms,
            "actor_display_name": run.actor_display_name,
            "warnings": json.loads(run.warnings_json or "[]"),
            "errors": json.loads(run.errors_json or "[]"),
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
