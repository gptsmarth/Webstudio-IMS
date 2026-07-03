"""Enterprise Deployment Engine — orchestrated release deployment with automatic rollback (M13D)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationType,
)
from webstudio_backend.infrastructure.database.models.release_deployment_run import (
    ReleaseDeploymentRun,
)
from webstudio_backend.infrastructure.repositories.release_deployment_run_repository import (
    ReleaseDeploymentRunRepository,
)
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.deployment_platform_adapter import DeploymentPlatformAdapter
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.release_manifest_validator import validate_release_manifest
from webstudio_backend.services.release_storage_paths import resolve_release_updates_root
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService

DEPLOYMENT_STEPS: tuple[str, ...] = (
    "create_database_backup",
    "backup_scheduler_state",
    "backup_configuration",
    "backup_windows_service_config",
    "validate_package",
    "stop_backend_service",
    "replace_backend",
    "run_alembic_migrations",
    "restart_windows_service",
    "restore_scheduler_state",
    "resume_backup_scheduler",
    "resume_notification_scheduler",
    "resume_tally_scheduler",
    "run_health_checks",
    "notify_desktop_clients",
    "mark_catalog_current",
    "deployment_completed",
)


class EnterpriseDeploymentEngine:
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
        self._runs = ReleaseDeploymentRunRepository(session)
        self._release_repo = SoftwareReleaseRepository(session)

    async def execute_deploy(
        self,
        *,
        job_id: int,
        user_id: int,
        release_version: str,
        build_number: int,
        release_channel,
        bundle_dir: str,
    ) -> dict[str, Any]:
        current_release = await self._release_repo.get_current(release_channel)
        previous_release_id = current_release.id if current_release else None

        run = await self._runs.create(
            ReleaseDeploymentRun(
                job_id=job_id,
                release_version=release_version,
                build_number=build_number,
                release_channel=release_channel,
                status="running",
                previous_release_id=previous_release_id,
                bundle_dir=bundle_dir,
                performed_by_user_id=user_id,
            ),
        )
        await self._session.commit()

        snapshot_root = self._deployment_snapshot_root(run.id)
        failed_step: str | None = None
        error_message: str | None = None

        try:
            for step in DEPLOYMENT_STEPS:
                detail = await self._execute_step(
                    run, step, snapshot_root=snapshot_root, user_id=user_id
                )
                await self._runs.mark_step(run, step=step, status="completed", detail=detail)
                await self._session.commit()
        except Exception as exc:
            failed_step = run.current_step or "unknown"
            error_message = str(exc)
            logger.exception("deployment.step_failed", step=failed_step, error=error_message)
            await self._runs.mark_step(run, step=failed_step, status="failed", error=error_message)
            run.status = "rolling_back"
            run.error_message = error_message
            await self._runs.save(run)
            await self._session.commit()
            await self._rollback(run, user_id=user_id)
            raise

        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.current_step = "deployment_completed"
        await self._runs.save(run)
        await self._session.commit()
        return self.serialize_run(run)

    async def _execute_step(
        self,
        run: ReleaseDeploymentRun,
        step: str,
        *,
        snapshot_root: Path,
        user_id: int,
    ) -> dict[str, Any]:
        run.current_step = step
        await self._runs.save(run)

        if step == "create_database_backup":
            engine = BackupEngine(self._session, self._settings)
            backup = await engine.create_backup(
                backup_type="full",
                trigger_type="pre_deploy",
                creator_user_id=user_id,
                creator_display_name="Deployment Engine",
            )
            run.pre_backup_run_id = backup.id
            run.pre_backup_filename = backup.filename
            await self._runs.save(run)
            return {"backup_id": backup.id, "filename": backup.filename}

        if step == "backup_scheduler_state":
            scheduler = SchedulerRuntimeService(self._session)
            snapshot = await scheduler.export_snapshot()
            run.scheduler_snapshot = snapshot
            await self._runs.save(run)
            return {"scheduler_keys": list(snapshot.keys())}

        if step == "backup_configuration":
            path = self._platform.snapshot_configuration(snapshot_root)
            run.config_snapshot_path = str(path)
            await self._runs.save(run)
            return {"path": str(path)}

        if step == "backup_windows_service_config":
            path = self._platform.snapshot_service_configuration(snapshot_root)
            run.service_config_snapshot_path = str(path)
            await self._runs.save(run)
            return {"path": str(path)}

        if step == "validate_package":
            bundle = Path(run.bundle_dir or "")
            manifest_path = bundle / "version-manifest.json"
            if not manifest_path.is_file():
                raise ValueError("version-manifest.json missing from bundle")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validation = validate_release_manifest(manifest)
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
            return {"manifest_valid": True}

        if step == "stop_backend_service":
            return await self._platform.stop_backend_service()

        if step == "replace_backend":
            if self._settings.is_test and not Path(run.bundle_dir or "").is_dir():
                return {"mode": "skipped", "reason": "bundle_missing_in_test"}
            return self._platform.replace_backend(Path(run.bundle_dir or ""))

        if step == "run_alembic_migrations":
            if self._settings.is_test:
                return {"mode": "skipped", "reason": "test_environment"}
            bundle = Path(run.bundle_dir) if run.bundle_dir else None
            return self._platform.run_alembic_migrations(bundle)

        if step == "restart_windows_service":
            return await self._platform.restart_backend_service()

        if step == "restore_scheduler_state":
            if run.scheduler_snapshot:
                scheduler = SchedulerRuntimeService(self._session)
                await scheduler.apply_snapshot(run.scheduler_snapshot)
            return {"restored": bool(run.scheduler_snapshot)}

        if step == "resume_backup_scheduler":
            return await self._resume_scheduler("backup")

        if step == "resume_notification_scheduler":
            return await self._resume_scheduler("notification_delivery")

        if step == "resume_tally_scheduler":
            return await self._resume_scheduler("tally_sync")

        if step == "run_health_checks":
            return await self._run_health_checks()

        if step == "notify_desktop_clients":
            return await self._notify_clients(run, user_id=user_id)

        if step == "mark_catalog_current":
            return await self._mark_catalog_current(run, user_id=user_id)

        if step == "deployment_completed":
            return {"release_version": run.release_version, "build_number": run.build_number}

        raise ValueError(f"Unknown deployment step: {step}")

    async def _resume_scheduler(self, scheduler_key: str) -> dict[str, str]:
        scheduler = SchedulerRuntimeService(self._session)
        await scheduler.record_run(scheduler_key, status="resumed_after_deploy")
        return {"scheduler_key": scheduler_key, "status": "resumed"}

    async def _run_health_checks(self) -> dict[str, Any]:
        checks: dict[str, str] = {"database": "unknown", "migrations": "unknown"}
        result = await self._session.execute(text("SELECT 1"))
        checks["database"] = "ok" if result.scalar_one() == 1 else "failed"
        migration_result = await self._session.execute(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        version = migration_result.scalar_one_or_none()
        checks["migrations"] = "ok" if version else "failed"
        if checks["database"] != "ok" or checks["migrations"] != "ok":
            raise RuntimeError(f"Health checks failed: {checks}")
        return checks

    async def _notify_clients(self, run: ReleaseDeploymentRun, *, user_id: int) -> dict[str, Any]:
        from webstudio_backend.services.notification_service import NotificationService

        notifications = NotificationService(self._session)
        notification = await notifications.create_notification(
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            severity=NotificationSeverity.INFO,
            title="Deployment completed",
            message=(
                f"WEBSTUDIO IMS {run.release_version} (build {run.build_number}) "
                "has been deployed successfully. Desktop clients will reconnect automatically."
            ),
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
            created_by_user_id=user_id,
        )
        return {"notification_id": notification.id}

    async def _mark_catalog_current(
        self, run: ReleaseDeploymentRun, *, user_id: int
    ) -> dict[str, Any]:
        await self._release_repo.clear_current_flags(run.release_channel)
        release = await self._release_repo.find_existing(
            release_version=run.release_version,
            build_number=run.build_number,
            channel=run.release_channel,
        )
        if release is None:
            raise ValueError("Release metadata not found in catalog")
        release.is_current = True
        release.published_by_user_id = user_id
        release.published_at = datetime.now(UTC)
        await self._release_repo.upsert_release(release)
        release_payload = EnterpriseReleaseService._serialize_release(release)  # noqa: SLF001
        from webstudio_backend.services.client_update_service import ClientUpdateService

        await ClientUpdateService(
            self._session, self._settings
        ).sync_platform_settings_from_release(
            release_payload,
        )
        return {"release_id": release.id}

    async def _rollback(self, run: ReleaseDeploymentRun, *, user_id: int) -> None:
        rollback_steps: list[str] = []
        try:
            if run.pre_backup_filename:
                restore = RestoreEngine(self._session, self._settings)
                result = await restore.execute_restore(
                    filename=run.pre_backup_filename,
                    restore_scope="entire_database",
                    create_emergency_backup=False,
                    confirmed=True,
                    actor_user_id=user_id,
                    actor_display_name="Deployment Engine Rollback",
                    rollback=True,
                )
                rollback_steps.append(f"database_restored:{result.filename}")
                if not result.success:
                    raise RuntimeError("Database rollback restore verification failed")

            if run.previous_release_id is not None:
                previous = await self._release_repo.get_by_id(run.previous_release_id)
                if previous is not None:
                    await self._release_repo.clear_current_flags(run.release_channel)
                    previous.is_current = True
                    await self._release_repo.upsert_release(previous)
                    rollback_steps.append(f"catalog_reverted:{previous.release_version}")

            if run.scheduler_snapshot:
                scheduler = SchedulerRuntimeService(self._session)
                await scheduler.apply_snapshot(run.scheduler_snapshot)
                rollback_steps.append("scheduler_state_restored")

            await self._platform.restart_backend_service()
            rollback_steps.append("service_restarted")

            run.status = "rolled_back"
            run.completed_at = datetime.now(UTC)
            run.error_message = (
                run.error_message or ""
            ) + f" | rollback: {', '.join(rollback_steps)}"
            await self._runs.save(run)
            await self._session.commit()
        except Exception as exc:
            logger.exception("deployment.rollback_failed", error=str(exc))
            run.status = "failed"
            run.error_message = f"{run.error_message} | rollback_failed: {exc}"
            await self._runs.save(run)
            await self._session.commit()

    def _deployment_snapshot_root(self, run_id: int) -> Path:
        root = resolve_release_updates_root(self._settings) / "deployment-runs" / str(run_id)
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def get_run(self, run_id: int) -> dict[str, Any] | None:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            return None
        return self.serialize_run(run)

    async def get_latest_run(self) -> dict[str, Any] | None:
        run = await self._runs.get_latest()
        if run is None:
            return None
        return self.serialize_run(run)

    @staticmethod
    def serialize_run(run: ReleaseDeploymentRun) -> dict[str, Any]:
        return {
            "run_id": run.id,
            "job_id": run.job_id,
            "release_version": run.release_version,
            "build_number": run.build_number,
            "release_channel": run.release_channel.value,
            "status": run.status,
            "current_step": run.current_step,
            "steps": run.steps_json or [],
            "pre_backup_run_id": run.pre_backup_run_id,
            "pre_backup_filename": run.pre_backup_filename,
            "rollback_backup_run_id": run.rollback_backup_run_id,
            "previous_release_id": run.previous_release_id,
            "bundle_dir": run.bundle_dir,
            "error_message": run.error_message,
            "performed_by_user_id": run.performed_by_user_id,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
