"""Enterprise Rollback Platform — full-stack rollback with permanent history (M13F)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationType,
    ReleaseDownloadStatus,
)
from webstudio_backend.infrastructure.database.models.enterprise_rollback_run import (
    EnterpriseRollbackRun,
)
from webstudio_backend.infrastructure.database.models.release_deployment_run import (
    ReleaseDeploymentRun,
)
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.enterprise_rollback_run_repository import (
    EnterpriseRollbackRunRepository,
)
from webstudio_backend.infrastructure.repositories.release_deployment_run_repository import (
    ReleaseDeploymentRunRepository,
)
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.client_update_service import ClientUpdateService
from webstudio_backend.services.deployment_platform_adapter import DeploymentPlatformAdapter
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService

ROLLBACK_STEPS: tuple[str, ...] = (
    "create_pre_rollback_safety_backup",
    "stop_backend_service",
    "restore_database",
    "restore_configuration",
    "restore_windows_service_config",
    "restore_backend",
    "restore_scheduler_state",
    "restore_release_metadata",
    "restore_deployment_metadata",
    "sync_client_platform_settings",
    "restart_windows_service",
    "resume_schedulers",
    "run_health_checks",
    "notify_connected_clients",
    "rollback_completed",
)


@dataclass(slots=True)
class RollbackContext:
    channel: Any
    current_release: SoftwareRelease
    target_release: SoftwareRelease
    deployment_run: ReleaseDeploymentRun | None
    database_backup_filename: str
    scheduler_snapshot: dict[str, Any]
    config_snapshot_path: str | None
    service_config_snapshot_path: str | None
    target_bundle_dir: str | None


class EnterpriseRollbackEngine:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        platform: DeploymentPlatformAdapter | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._platform = platform or DeploymentPlatformAdapter(settings)
        self._runs = EnterpriseRollbackRunRepository(session)
        self._deployment_runs = ReleaseDeploymentRunRepository(session)
        self._release_repo = SoftwareReleaseRepository(session)
        self._enterprise = EnterpriseReleaseService(session, settings)

    async def execute_rollback(
        self,
        *,
        user_id: int,
        deployment_event_id: int | None = None,
    ) -> dict[str, Any]:
        context = await self._resolve_context()
        run = await self._runs.create(
            EnterpriseRollbackRun(
                release_channel=context.channel,
                status="running",
                from_release_version=context.current_release.release_version,
                from_build_number=context.current_release.build_number,
                from_release_id=context.current_release.id,
                to_release_version=context.target_release.release_version,
                to_build_number=context.target_release.build_number,
                to_release_id=context.target_release.id,
                deployment_run_id=context.deployment_run.id if context.deployment_run else None,
                deployment_event_id=deployment_event_id,
                database_restore_filename=context.database_backup_filename,
                scheduler_snapshot=context.scheduler_snapshot,
                config_snapshot_path=context.config_snapshot_path,
                service_config_snapshot_path=context.service_config_snapshot_path,
                target_bundle_dir=context.target_bundle_dir,
                performed_by_user_id=user_id,
            ),
        )
        await self._session.commit()

        try:
            for step in ROLLBACK_STEPS:
                detail = await self._execute_step(run, step, context=context, user_id=user_id)
                await self._runs.mark_step(run, step=step, status="completed", detail=detail)
                await self._session.commit()
        except Exception as exc:
            logger.exception("rollback.step_failed", step=run.current_step, error=str(exc))
            await self._runs.mark_step(
                run,
                step=run.current_step or "unknown",
                status="failed",
                error=str(exc),
            )
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(UTC)
            await self._runs.save(run)
            await self._session.commit()
            raise

        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.current_step = "rollback_completed"
        await self._runs.save(run)
        await self._session.commit()
        return self.serialize_run(run)

    async def _resolve_context(self) -> RollbackContext:
        channel = self._enterprise.resolve_channel()
        rows, _ = await self._release_repo.list_history(
            channel, page=PageParams(page=1, page_size=5)
        )
        if len(rows) < 2:
            raise ValueError("No previous release available for rollback")
        current = next((row for row in rows if row.is_current), rows[0])
        target = next((row for row in rows if row.id != current.id), None)
        if target is None:
            raise ValueError("No previous release available for rollback")

        deployment_run = await self._find_deployment_run_for_release(current)
        database_backup = await self._resolve_database_backup(deployment_run)
        scheduler_snapshot = dict(deployment_run.scheduler_snapshot) if deployment_run else {}
        if not scheduler_snapshot:
            scheduler_snapshot = await SchedulerRuntimeService(self._session).export_snapshot()

        config_path = deployment_run.config_snapshot_path if deployment_run else None
        service_path = deployment_run.service_config_snapshot_path if deployment_run else None
        bundle_dir = await self._resolve_target_bundle(target)

        return RollbackContext(
            channel=channel,
            current_release=current,
            target_release=target,
            deployment_run=deployment_run,
            database_backup_filename=database_backup,
            scheduler_snapshot=scheduler_snapshot,
            config_snapshot_path=config_path,
            service_config_snapshot_path=service_path,
            target_bundle_dir=bundle_dir,
        )

    async def _find_deployment_run_for_release(
        self,
        release: SoftwareRelease,
    ) -> ReleaseDeploymentRun | None:
        result = await self._session.execute(
            select(ReleaseDeploymentRun)
            .where(
                ReleaseDeploymentRun.release_version == release.release_version,
                ReleaseDeploymentRun.build_number == release.build_number,
                ReleaseDeploymentRun.release_channel == release.release_channel,
            )
            .order_by(desc(ReleaseDeploymentRun.created_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def _resolve_database_backup(self, deployment_run: ReleaseDeploymentRun | None) -> str:
        if self._settings.is_test:
            if deployment_run and deployment_run.pre_backup_filename:
                return deployment_run.pre_backup_filename
            return "webstudio-backup-test-rollback.tar.gz"

        if deployment_run and deployment_run.pre_backup_filename:
            return deployment_run.pre_backup_filename

        from webstudio_backend.infrastructure.repositories.backup_run_repository import (
            BackupRunRepository,
        )

        for backup in await BackupRunRepository(self._session).list_recent(limit=20):
            if backup.trigger_type == "pre_deploy" and backup.status == "completed":
                return backup.filename
        raise ValueError("No pre-deploy database backup found for rollback")

    async def _resolve_target_bundle(self, target: SoftwareRelease) -> str | None:
        result = await self._session.execute(
            select(ReleaseDownloadJob)
            .where(
                ReleaseDownloadJob.release_version == target.release_version,
                ReleaseDownloadJob.build_number == target.build_number,
                ReleaseDownloadJob.release_channel == target.release_channel,
                ReleaseDownloadJob.status == ReleaseDownloadStatus.COMPLETED,
            )
            .order_by(desc(ReleaseDownloadJob.completed_at))
            .limit(1),
        )
        job = result.scalar_one_or_none()
        if job and job.bundle_dir:
            return job.bundle_dir

        catalog_root = self._enterprise._resolve_catalog_root()  # noqa: SLF001
        if catalog_root is not None:
            bundle = catalog_root / f"v{target.release_version}"
            if bundle.is_dir():
                return str(bundle)
        return None

    async def _execute_step(
        self,
        run: EnterpriseRollbackRun,
        step: str,
        *,
        context: RollbackContext,
        user_id: int,
    ) -> dict[str, Any]:
        run.current_step = step
        await self._runs.save(run)

        if step == "create_pre_rollback_safety_backup":
            if self._settings.is_test:
                return {"mode": "skipped", "reason": "test_environment"}
            engine = BackupEngine(self._session, self._settings)
            backup = await engine.create_backup(
                backup_type="full",
                trigger_type="pre_rollback",
                creator_user_id=user_id,
                creator_display_name="Rollback Engine",
            )
            run.pre_rollback_backup_filename = backup.filename
            await self._runs.save(run)
            return {"filename": backup.filename}

        if step == "stop_backend_service":
            return await self._platform.stop_backend_service()

        if step == "restore_database":
            if self._settings.is_test:
                return {"mode": "skipped", "filename": context.database_backup_filename}
            restore = RestoreEngine(self._session, self._settings)
            result = await restore.execute_restore(
                filename=context.database_backup_filename,
                restore_scope="entire_database",
                create_emergency_backup=False,
                confirmed=True,
                actor_user_id=user_id,
                actor_display_name="Enterprise Rollback Engine",
                rollback=True,
            )
            if not result.success:
                raise RuntimeError("Database restore verification failed during rollback")
            return {"filename": result.filename, "verification": result.verification_status}

        if step == "restore_configuration":
            if context.config_snapshot_path:
                return self._platform.restore_configuration(context.config_snapshot_path)
            return {"mode": "skipped", "reason": "no_config_snapshot"}

        if step == "restore_windows_service_config":
            if context.service_config_snapshot_path:
                return self._platform.restore_service_configuration(
                    context.service_config_snapshot_path
                )
            return {"mode": "skipped", "reason": "no_service_snapshot"}

        if step == "restore_backend":
            if context.target_bundle_dir and Path(context.target_bundle_dir).is_dir():
                if self._settings.is_test:
                    return {"mode": "dry_run", "bundle": context.target_bundle_dir}
                return self._platform.replace_backend(Path(context.target_bundle_dir))
            return {"mode": "skipped", "reason": "bundle_missing"}

        if step == "restore_scheduler_state":
            if context.scheduler_snapshot:
                scheduler = SchedulerRuntimeService(self._session)
                await scheduler.apply_snapshot(context.scheduler_snapshot)
            return {"restored": bool(context.scheduler_snapshot)}

        if step == "restore_release_metadata":
            await self._release_repo.clear_current_flags(context.channel)
            context.target_release.is_current = True
            context.target_release.published_by_user_id = user_id
            context.target_release.published_at = datetime.now(UTC)
            await self._release_repo.upsert_release(context.target_release)
            return {
                "from_version": context.current_release.release_version,
                "to_version": context.target_release.release_version,
                "to_release_id": context.target_release.id,
            }

        if step == "restore_deployment_metadata":
            if context.deployment_run is not None:
                context.deployment_run.status = "rolled_back"
                context.deployment_run.completed_at = datetime.now(UTC)
                await self._deployment_runs.save(context.deployment_run)
            return {
                "deployment_run_id": context.deployment_run.id if context.deployment_run else None,
                "deployment_event_id": run.deployment_event_id,
            }

        if step == "sync_client_platform_settings":
            payload = EnterpriseReleaseService._serialize_release(
                context.target_release
            )  # noqa: SLF001
            await ClientUpdateService(
                self._session, self._settings
            ).sync_platform_settings_from_release(payload)
            return {"release_version": context.target_release.release_version}

        if step == "restart_windows_service":
            return await self._platform.restart_backend_service()

        if step == "resume_schedulers":
            scheduler = SchedulerRuntimeService(self._session)
            resumed = []
            for key in ("backup", "notification_delivery", "tally_sync"):
                await scheduler.record_run(key, status="resumed_after_rollback")
                resumed.append(key)
            return {"resumed": resumed}

        if step == "run_health_checks":
            checks = await self._run_health_checks()
            run.health_status = checks
            await self._runs.save(run)
            if checks.get("database") != "ok" or checks.get("migrations") != "ok":
                raise RuntimeError(f"Health checks failed after rollback: {checks}")
            return checks

        if step == "notify_connected_clients":
            from webstudio_backend.services.notification_service import NotificationService

            notifications = NotificationService(self._session)
            notification = await notifications.create_notification(
                notification_type=NotificationType.SYSTEM_NOTIFICATION,
                severity=NotificationSeverity.WARNING,
                title="Server rollback completed",
                message=(
                    f"WEBSTUDIO IMS was rolled back to {context.target_release.release_version} "
                    f"(build {context.target_release.build_number}). "
                    "Desktop and mobile clients will reconnect automatically."
                ),
                category=NotificationCategory.SYSTEM,
                created_by=NotificationCreator.SYSTEM,
                created_by_user_id=user_id,
            )
            return {"notification_id": notification.id}

        if step == "rollback_completed":
            return {
                "from_version": context.current_release.release_version,
                "to_version": context.target_release.release_version,
            }

        raise ValueError(f"Unknown rollback step: {step}")

    async def _run_health_checks(self) -> dict[str, str]:
        checks: dict[str, str] = {
            "database": "unknown",
            "migrations": "unknown",
            "status": "unknown",
        }
        result = await self._session.execute(text("SELECT 1"))
        checks["database"] = "ok" if result.scalar_one() == 1 else "failed"
        migration_result = await self._session.execute(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        version = migration_result.scalar_one_or_none()
        checks["migrations"] = "ok" if version else "failed"
        checks["status"] = (
            "ok" if checks["database"] == "ok" and checks["migrations"] == "ok" else "degraded"
        )
        return checks

    async def get_run(self, run_id: int) -> dict[str, Any] | None:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            return None
        return self.serialize_run(run)

    async def list_history(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        rows, total = await self._runs.list_history(page=PageParams(page=page, page_size=page_size))
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
        return {
            "items": [self.serialize_run(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "permanent_history": True,
        }

    @staticmethod
    def serialize_run(run: EnterpriseRollbackRun) -> dict[str, Any]:
        return {
            "run_id": run.id,
            "status": run.status,
            "current_step": run.current_step,
            "steps": run.steps_json or [],
            "release_channel": run.release_channel.value,
            "from_release_version": run.from_release_version,
            "from_build_number": run.from_build_number,
            "from_release_id": run.from_release_id,
            "to_release_version": run.to_release_version,
            "to_build_number": run.to_build_number,
            "to_release_id": run.to_release_id,
            "deployment_run_id": run.deployment_run_id,
            "deployment_event_id": run.deployment_event_id,
            "pre_rollback_backup_filename": run.pre_rollback_backup_filename,
            "database_restore_filename": run.database_restore_filename,
            "config_snapshot_path": run.config_snapshot_path,
            "service_config_snapshot_path": run.service_config_snapshot_path,
            "target_bundle_dir": run.target_bundle_dir,
            "health_status": run.health_status or {},
            "performed_by_user_id": run.performed_by_user_id,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
