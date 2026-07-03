"""Maintenance scheduler — storage and system health probes."""

from __future__ import annotations

import shutil

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)
from webstudio_backend.services.startup_orchestrator import _storage_path, verify_storage

MAINTENANCE_INTERVAL_SECONDS = 3600


async def maybe_run_maintenance_checks() -> None:
    settings = get_settings()
    storage = await verify_storage(settings)
    async with session_scope() as session:
        runtime = SchedulerRuntimeService(session)
        path = _storage_path(settings)
        usage = shutil.disk_usage(str(path))
        await runtime.record_run(
            "maintenance",
            status=storage.status,
            interval_seconds=MAINTENANCE_INTERVAL_SECONDS,
            state_patch={
                "storage_path": str(path),
                "free_bytes": usage.free,
                "total_bytes": usage.total,
                "detail": storage.detail,
            },
        )
        await session.commit()


async def maintenance_scheduler_loop() -> None:
    while not is_shutdown_requested():
        if not await sleep_until_next_run("maintenance", interval_seconds=MAINTENANCE_INTERVAL_SECONDS):
            break
        try:
            await maybe_run_maintenance_checks()
        except Exception:
            async with session_scope() as session:
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    "maintenance",
                    status="failed",
                    interval_seconds=MAINTENANCE_INTERVAL_SECONDS,
                )
                await session.commit()
