"""Background ASUS live-price refresh jobs (non-blocking for API requests).

Mirrors the structure of ``product_image_jobs.py``. One notable
simplification versus that module: ``live_price_checked_at`` is updated on
every attempt (success or failure, see
``ProductModelRepository.update_live_price``), so the "who's due" query
naturally self-throttles — no separate failure-cooldown map is needed the
way missing-image backfill needs one (a missing image stays missing forever
with nothing marking "recently tried").

The refresh cadence (default 30 days) is admin-configurable via the
``asus_price_refresh_stale_days`` system setting (Settings > Integrations),
so a real Gemini API call is never wasted more often than the admin wants —
see ``_get_stale_after_days``.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.session import get_session_factory
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.asus_live_price_service import refresh_asus_live_price
from webstudio_backend.services.scheduler_runtime_service import sleep_until_next_run

_inflight: dict[str, asyncio.Task[None]] = {}
_DEFAULT_STALE_AFTER_DAYS = 30
_MIN_STALE_AFTER_DAYS = 1
_MAX_STALE_AFTER_DAYS = 90
_BACKFILL_SWEEP_INTERVAL_SECONDS = 6 * 60 * 60  # check every 6 hours what's due
_BACKFILL_BATCH_SIZE = 10
# A real Gemini API call per job (unlike the free-scraping image jobs) — keep
# this low regardless of catalog size or how large a bulk refresh is.
_MAX_CONCURRENT_ASUS_PRICE_JOBS = 2
_concurrency_limiter = asyncio.Semaphore(_MAX_CONCURRENT_ASUS_PRICE_JOBS)

# Tracks the most recent bulk "Update prices" run so any client (desktop or
# mobile) can poll real server-side progress regardless of which page it's
# on, whether it triggered the run itself, or whether it was reopened after
# the run had already started or finished. Server-side rather than
# client-side state so multiple frontends/devices see the same truth, and so
# navigating away and back (or restarting the app) doesn't lose the picture.
_bulk_run: dict[str, Any] | None = None


def is_asus_price_job_running(model_id: uuid.UUID | str) -> bool:
    key = str(model_id)
    task = _inflight.get(key)
    return task is not None and not task.done()


def schedule_asus_price_refresh(
    model_id: uuid.UUID | str,
    *,
    force: bool = False,  # noqa: ARG001 — kept for call-site parity/future use; see module docstring
) -> bool:
    """Start a background live-price refresh if not already running.

    Returns True if scheduled. Safe to call unconditionally for any model —
    ``refresh_asus_live_price`` itself no-ops for non-ASUS models. Unlike
    the image-resolve scheduler, there's no failure cooldown to bypass here
    (see module docstring), so `force` currently has no behavioral effect —
    it's kept so call sites read the same way as `schedule_product_image_resolve`.
    """
    key = str(model_id)
    existing = _inflight.get(key)
    if existing is not None and not existing.done():
        return False

    task = asyncio.create_task(
        _run_asus_price_refresh(uuid.UUID(str(model_id))), name=f"asus-live-price:{key}"
    )
    _inflight[key] = task

    def _cleanup(done: asyncio.Task[None]) -> None:
        current = _inflight.get(key)
        if current is done:
            _inflight.pop(key, None)

    task.add_done_callback(_cleanup)
    return True


async def _run_asus_price_refresh(model_id: uuid.UUID) -> None:
    key = str(model_id)
    try:
        async with _concurrency_limiter:
            factory = get_session_factory()
            async with factory() as session:
                status = await refresh_asus_live_price(session, model_id)
                await session.commit()
                logger.debug("ASUS live price refresh for {} finished: {}", model_id, status)
    except Exception:
        logger.exception("ASUS live price refresh failed unexpectedly for model {}", model_id)
    finally:
        _inflight.pop(key, None)


async def _get_stale_after_days(session: AsyncSession) -> int:
    days = await SystemSettingRepository(session).get_int(
        "asus_price_refresh_stale_days", default=_DEFAULT_STALE_AFTER_DAYS
    )
    return max(_MIN_STALE_AFTER_DAYS, min(days, _MAX_STALE_AFTER_DAYS))


async def schedule_due_asus_price_refreshes(*, limit: int = _BACKFILL_BATCH_SIZE) -> int:
    """Queue background refresh for ASUS models whose price hasn't been
    checked within the admin-configured interval. Returns how many jobs were
    newly scheduled."""
    factory = get_session_factory()
    async with factory() as session:
        stale_days = await _get_stale_after_days(session)
        stale_before = datetime.now(UTC) - timedelta(days=stale_days)
        repo = ProductModelRepository(session)
        model_ids = await repo.list_ids_needing_asus_price_refresh(
            stale_before=stale_before, limit=max(limit * 3, limit)
        )

    scheduled = 0
    for model_id in model_ids:
        if scheduled >= limit:
            break
        if schedule_asus_price_refresh(model_id):
            scheduled += 1
    if scheduled:
        logger.info("ASUS live price backfill scheduled {} model(s)", scheduled)
    return scheduled


async def schedule_all_asus_price_refreshes() -> int:
    """Manual bulk "Update prices" trigger — refreshes every active ASUS
    model right away, regardless of when it was last checked."""
    factory = get_session_factory()
    async with factory() as session:
        repo = ProductModelRepository(session)
        model_ids = await repo.list_ids_for_asus_brand()

    scheduled_keys: list[str] = []
    for model_id in model_ids:
        if schedule_asus_price_refresh(model_id, force=True):
            scheduled_keys.append(str(model_id))
    _start_bulk_run_tracking(scheduled_keys)
    logger.info("ASUS live price bulk refresh scheduled {} model(s)", len(scheduled_keys))
    return len(scheduled_keys)


def _start_bulk_run_tracking(model_keys: list[str]) -> None:
    """Begin tracking a fresh bulk run, replacing whatever run was tracked
    before (there's only ever one "current/most recent" bulk run — matches
    the "Update prices" button being a single admin-triggered action rather
    than something concurrent runs need to be distinguished between)."""
    global _bulk_run
    now = datetime.now(UTC).isoformat()
    remaining = set(model_keys)
    run: dict[str, Any] = {
        "total": len(model_keys),
        "remaining": remaining,
        "started_at": now,
        "finished_at": now if not model_keys else None,
    }
    _bulk_run = run

    for key in model_keys:
        task = _inflight.get(key)
        if task is None or task.done():
            # Finished (or was never actually scheduled) before we could
            # attach a callback — count it as already done.
            remaining.discard(key)
            continue
        task.add_done_callback(lambda _task, k=key, r=run: _on_bulk_run_job_done(r, k))

    if not remaining and run["finished_at"] is None:
        run["finished_at"] = datetime.now(UTC).isoformat()


def _on_bulk_run_job_done(run: dict[str, Any], model_key: str) -> None:
    # Guard against a stale callback firing after a newer bulk run replaced
    # this one in `_bulk_run` — only ever mutate the run it was attached to.
    run["remaining"].discard(model_key)
    if not run["remaining"] and run["finished_at"] is None:
        run["finished_at"] = datetime.now(UTC).isoformat()


def get_asus_bulk_run_status() -> dict[str, Any]:
    """Real progress for the most recent bulk "Update prices" run, if any
    has happened this server session. `total`/`completed`/`in_progress`
    reflect only that specific run's models, not unrelated single-model or
    scheduled-sweep refreshes that might also be running concurrently."""
    run = _bulk_run
    if run is None:
        return {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "started_at": None,
            "finished_at": None,
        }
    remaining = len(run["remaining"])
    total = run["total"]
    return {
        "total": total,
        "completed": total - remaining,
        "in_progress": remaining,
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
    }


async def asus_live_price_backfill_loop() -> None:
    """Periodically refresh ASUS models whose live price has gone stale."""
    while True:
        if not await sleep_until_next_run(
            "asus_live_price_backfill",
            interval_seconds=_BACKFILL_SWEEP_INTERVAL_SECONDS,
        ):
            return
        try:
            await schedule_due_asus_price_refreshes()
        except Exception:
            logger.exception("ASUS live price backfill cycle failed")
