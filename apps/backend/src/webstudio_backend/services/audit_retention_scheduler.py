"""Background loop that purges audit logs past the retention window."""

from __future__ import annotations

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.services.audit_retention_service import AuditRetentionService
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)

AUDIT_RETENTION_INTERVAL_SECONDS = 86_400


async def maybe_purge_audit_logs() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        deleted = await AuditRetentionService(session).purge_expired()
        runtime = SchedulerRuntimeService(session)
        await runtime.record_run(
            "audit_retention",
            status="completed" if deleted else "ok",
            interval_seconds=AUDIT_RETENTION_INTERVAL_SECONDS,
            state_patch={"deleted_rows": deleted},
        )
        if deleted:
            await session.commit()
        else:
            await session.commit()


async def audit_retention_loop() -> None:
    while not is_shutdown_requested():
        if not await sleep_until_next_run("audit_retention", interval_seconds=AUDIT_RETENTION_INTERVAL_SECONDS):
            break
        try:
            await maybe_purge_audit_logs()
        except Exception:
            async with session_scope() as session:
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    "audit_retention",
                    status="failed",
                    interval_seconds=AUDIT_RETENTION_INTERVAL_SECONDS,
                )
                await session.commit()
