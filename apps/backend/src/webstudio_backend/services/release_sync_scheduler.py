"""Background GitHub release synchronization loop (M13B)."""

from __future__ import annotations

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.services.github_release_sync_service import (
    RELEASE_SYNC_SCHEDULER_KEY,
    GitHubReleaseSyncService,
)
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)


async def maybe_sync_github_releases() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        service = GitHubReleaseSyncService(session, settings)
        interval = settings.release_sync_interval_seconds
        if not await service.is_enabled():
            runtime = SchedulerRuntimeService(session)
            await runtime.record_run(
                RELEASE_SYNC_SCHEDULER_KEY,
                status="disabled",
                interval_seconds=interval,
            )
            await session.commit()
            return
        try:
            await service.run_sync_cycle()
        except Exception as exc:
            runtime = SchedulerRuntimeService(session)
            await runtime.record_run(
                RELEASE_SYNC_SCHEDULER_KEY,
                status="failed",
                interval_seconds=interval,
                state_patch={"detail": str(exc)},
            )
        await session.commit()


async def release_sync_loop() -> None:
    settings = get_settings()
    interval = settings.release_sync_interval_seconds
    while not is_shutdown_requested():
        if not await sleep_until_next_run(RELEASE_SYNC_SCHEDULER_KEY, interval_seconds=interval):
            break
        try:
            await maybe_sync_github_releases()
        except Exception:
            async with session_scope() as session:
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    RELEASE_SYNC_SCHEDULER_KEY,
                    status="failed",
                    interval_seconds=interval,
                )
                await session.commit()
