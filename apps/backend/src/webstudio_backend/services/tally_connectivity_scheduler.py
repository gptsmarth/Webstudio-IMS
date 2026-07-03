"""Background Tally workstation connectivity probe — tolerates laptop mobility."""

from __future__ import annotations

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService

PROBE_SCHEDULER_KEY = "tally_connectivity_probe"


async def maybe_probe_tally_connectivity() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        enabled = await SystemSettingRepository(session).get_bool("tally_enabled", default=False)
        runtime = SchedulerRuntimeService(session)
        interval = settings.tally_connectivity_probe_seconds
        if not enabled:
            await runtime.record_run(
                PROBE_SCHEDULER_KEY,
                status="disabled",
                interval_seconds=interval,
            )
            await session.commit()
            return
        status = "ok"
        detail = "Probe skipped"
        try:
            diagnostics = await TallyConnectivityService(session).test_connection()
            status = "ok" if diagnostics.reachable else "offline"
            detail = diagnostics.user_message or diagnostics.status
        except Exception as exc:
            status = "failed"
            detail = str(exc)
        await runtime.record_run(
            PROBE_SCHEDULER_KEY,
            status=status,
            interval_seconds=interval,
            state_patch={"detail": detail},
        )
        await session.commit()


async def tally_connectivity_probe_loop() -> None:
    settings = get_settings()
    interval = settings.tally_connectivity_probe_seconds
    while not is_shutdown_requested():
        if not await sleep_until_next_run(PROBE_SCHEDULER_KEY, interval_seconds=interval):
            break
        try:
            await maybe_probe_tally_connectivity()
        except Exception:
            async with session_scope() as session:
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    PROBE_SCHEDULER_KEY,
                    status="failed",
                    interval_seconds=interval,
                )
                await session.commit()
