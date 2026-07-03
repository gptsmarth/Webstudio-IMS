"""Notification delivery scheduler — resumes from persisted runtime state."""

from __future__ import annotations

from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)

NOTIFICATION_INTERVAL_SECONDS = 300


async def maybe_process_notification_delivery() -> None:
    async with session_scope() as session:
        settings = SystemSettingRepository(session)
        enabled = await settings.get_bool("notifications_enabled", default=True)
        runtime = SchedulerRuntimeService(session)
        status = "ok" if enabled else "disabled"
        await runtime.record_run(
            "notification_delivery",
            status=status,
            interval_seconds=NOTIFICATION_INTERVAL_SECONDS,
            state_patch={"notifications_enabled": enabled},
        )
        await session.commit()


async def notification_scheduler_loop() -> None:
    while not is_shutdown_requested():
        if not await sleep_until_next_run("notification_delivery", interval_seconds=NOTIFICATION_INTERVAL_SECONDS):
            break
        try:
            await maybe_process_notification_delivery()
        except Exception:
            async with session_scope() as session:
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    "notification_delivery",
                    status="failed",
                    interval_seconds=NOTIFICATION_INTERVAL_SECONDS,
                )
                await session.commit()
