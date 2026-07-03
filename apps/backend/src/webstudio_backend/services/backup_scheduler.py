"""Scheduled backup runner."""

from __future__ import annotations

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.backup_schedule import compute_next_scheduled_backup
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)

BACKUP_POLL_INTERVAL_SECONDS = 900


async def maybe_run_scheduled_backup() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        repo = SystemSettingRepository(session)
        schedule = await repo.get_string("backup_schedule") or "manual"
        runtime = SchedulerRuntimeService(session)
        if schedule == "manual":
            await runtime.record_run(
                "backup",
                status="manual",
                interval_seconds=BACKUP_POLL_INTERVAL_SECONDS,
                state_patch={"schedule": schedule},
            )
            await session.commit()
            return
        from datetime import UTC, datetime

        last_raw = await repo.get_string("last_backup_at")
        last_at = datetime.fromisoformat(last_raw) if last_raw else None
        next_at = compute_next_scheduled_backup(schedule, last_backup_at=last_at)
        if next_at is None or datetime.now(UTC) < next_at:
            await runtime.record_run(
                "backup",
                status="waiting",
                interval_seconds=BACKUP_POLL_INTERVAL_SECONDS,
                state_patch={
                    "schedule": schedule,
                    "next_scheduled_at": next_at.isoformat() if next_at else None,
                },
            )
            await session.commit()
            return
        storage_backend = await repo.get_string("backup_storage_backend") or "local"
        engine = BackupEngine(session, settings)
        await engine.create_backup(
            backup_type="full",
            trigger_type="scheduled",
            creator_display_name="Scheduled backup",
            storage_backend=storage_backend,
        )
        await runtime.record_run(
            "backup",
            status="completed",
            interval_seconds=BACKUP_POLL_INTERVAL_SECONDS,
            state_patch={"schedule": schedule, "trigger": "scheduled"},
        )
        await session.commit()


async def backup_scheduler_loop() -> None:
    while not is_shutdown_requested():
        if not await sleep_until_next_run("backup", interval_seconds=BACKUP_POLL_INTERVAL_SECONDS):
            break
        try:
            await maybe_run_scheduled_backup()
        except Exception as exc:
            from webstudio_backend.services.backup_alert_service import BackupAlertService

            async with session_scope() as session:
                await BackupAlertService(session).notify_scheduled_backup_failed(
                    detail=str(exc),
                )
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    "backup",
                    status="failed",
                    interval_seconds=BACKUP_POLL_INTERVAL_SECONDS,
                )
                await session.commit()
