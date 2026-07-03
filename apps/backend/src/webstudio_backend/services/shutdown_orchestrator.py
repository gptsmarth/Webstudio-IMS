"""Graceful shutdown orchestration for business-hours Windows deployments."""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger

from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    request_shutdown,
)


@dataclass(slots=True)
class ShutdownReport:
    steps: list[str] = field(default_factory=list)
    success: bool = True


async def checkpoint_tally_sync() -> None:
    from webstudio_backend.infrastructure.database.session import session_scope
    from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
        TallyCompanySyncRepository,
    )
    from webstudio_backend.infrastructure.repositories.tally_sync_history_repository import (
        TallySyncHistoryRepository,
    )

    async with session_scope() as session:
        company_repo = TallyCompanySyncRepository(session)
        history_repo = TallySyncHistoryRepository(session)
        companies = await company_repo.list_active()
        for company in companies:
            if not company.sync_in_progress:
                continue
            open_history = await history_repo.get_open_for_company(company.id)
            if open_history is not None:
                await history_repo.finalize(
                    open_history,
                    status="skipped",
                    invoices_checked=0,
                    invoices_imported=0,
                    invoices_skipped=0,
                    errors_count=0,
                    error_summary="Server shutdown — sync checkpointed",
                )
            await company_repo.update_sync_state(company, sync_in_progress=False)
            runtime = SchedulerRuntimeService(session)
            await runtime.persist_checkpoint(
                "tally_sync",
                state_patch={"shutdown_checkpoint_at": datetime.now(UTC).isoformat()},
            )
        await session.commit()
    logger.info("Tally sync checkpoint complete")


def flush_logs() -> None:
    for handler_id, handler in logger._core.handlers.items():  # noqa: SLF001
        sink = getattr(handler, "_sink", None)
        flush = getattr(sink, "flush", None)
        if callable(flush):
            flush()
    sys.stdout.flush()
    sys.stderr.flush()
    logger.info("Logs flushed")


async def persist_scheduler_state() -> None:
    from webstudio_backend.infrastructure.database.session import session_scope

    async with session_scope() as session:
        service = SchedulerRuntimeService(session)
        await service.snapshot_for_shutdown()
        await session.commit()


async def run_graceful_shutdown(*, wait_for_sync_seconds: float = 15.0) -> ShutdownReport:
    report = ShutdownReport()
    request_shutdown()
    report.steps.append("shutdown_requested")

    deadline = time.monotonic() + wait_for_sync_seconds
    from webstudio_backend.services.tally_sync_service import is_tally_sync_active

    while is_tally_sync_active() and time.monotonic() < deadline:
        await asyncio.sleep(0.5)
    report.steps.append("in_flight_requests_draining")

    try:
        await checkpoint_tally_sync()
        report.steps.append("tally_checkpoint")
    except Exception as exc:
        logger.warning("Tally checkpoint failed: {error}", error=exc)
        report.success = False

    try:
        await persist_scheduler_state()
        report.steps.append("scheduler_state_saved")
    except Exception as exc:
        logger.warning("Scheduler state persist failed: {error}", error=exc)
        report.success = False

    flush_logs()
    report.steps.append("logs_flushed")
    return report


def ensure_shutdown_requested() -> None:
    if not is_shutdown_requested():
        request_shutdown()
