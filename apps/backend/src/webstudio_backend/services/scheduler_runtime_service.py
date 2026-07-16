"""Persist and restore scheduler timing across server restarts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.scheduler_runtime_state import (
    SchedulerRuntimeState,
)
from webstudio_backend.infrastructure.repositories.scheduler_runtime_repository import (
    SchedulerRuntimeRepository,
)

DEFAULT_INTERVALS: dict[str, int] = {
    "tally_sync": 300,
    "backup": 900,
    "audit_retention": 86_400,
    "notification_delivery": 300,
    "maintenance": 3600,
    "tally_connectivity_probe": 120,
    "github_release_sync": 900,
    "product_image_backfill": 600,
}

_shutdown_requested = asyncio.Event()


def request_shutdown() -> None:
    _shutdown_requested.set()


def is_shutdown_requested() -> bool:
    return _shutdown_requested.is_set()


def reset_shutdown_flag() -> None:
    _shutdown_requested.clear()


class SchedulerRuntimeService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SchedulerRuntimeRepository(session)

    async def seconds_until_next_run(
        self,
        scheduler_key: str,
        *,
        interval_seconds: int | None = None,
    ) -> float:
        default_interval = interval_seconds or DEFAULT_INTERVALS.get(scheduler_key, 300)
        row = await self._repo.get_or_create(
            scheduler_key, default_interval_seconds=default_interval
        )
        interval = row.interval_seconds or default_interval
        now = datetime.now(UTC)
        if row.next_run_at is not None:
            remaining = (row.next_run_at - now).total_seconds()
            if remaining > 0:
                return remaining
        if row.last_run_at is not None:
            elapsed = (now - row.last_run_at).total_seconds()
            remaining = interval - elapsed
            if remaining > 0:
                return remaining
        return 0.0

    async def record_run(
        self,
        scheduler_key: str,
        *,
        status: str,
        interval_seconds: int | None = None,
        state_patch: dict[str, Any] | None = None,
    ) -> None:
        default_interval = interval_seconds or DEFAULT_INTERVALS.get(scheduler_key, 300)
        row = await self._repo.get_or_create(
            scheduler_key, default_interval_seconds=default_interval
        )
        interval = interval_seconds or row.interval_seconds or default_interval
        now = datetime.now(UTC)
        next_run = now + timedelta(seconds=interval)
        state_json = dict(row.state_json or {})
        if state_patch:
            state_json.update(state_patch)
        await self._repo.update_run(
            scheduler_key,
            last_run_at=now,
            last_run_status=status,
            next_run_at=next_run,
            state_json=state_json,
        )
        if row.interval_seconds != interval:
            row.interval_seconds = interval

    async def persist_checkpoint(
        self,
        scheduler_key: str,
        *,
        state_patch: dict[str, Any],
    ) -> None:
        await self._repo.merge_state_json(scheduler_key, state_patch)

    async def sync_interval(self, scheduler_key: str, interval_seconds: int) -> None:
        row = await self._repo.get_or_create(
            scheduler_key,
            default_interval_seconds=interval_seconds,
        )
        row.interval_seconds = interval_seconds

    async def get_next_run_at(self, scheduler_key: str) -> datetime | None:
        row = await self._repo.get(scheduler_key)
        return row.next_run_at if row is not None else None

    async def get_state(self, scheduler_key: str) -> SchedulerRuntimeState:
        return await self._repo.get_or_create(
            scheduler_key,
            default_interval_seconds=DEFAULT_INTERVALS.get(scheduler_key, 300),
        )

    async def restore_all(self) -> dict[str, dict[str, Any]]:
        restored: dict[str, dict[str, Any]] = {}
        for key, default_interval in DEFAULT_INTERVALS.items():
            row = await self._repo.get_or_create(key, default_interval_seconds=default_interval)
            restored[key] = {
                "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
                "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
                "last_run_status": row.last_run_status,
                "interval_seconds": row.interval_seconds,
                "state_json": dict(row.state_json or {}),
            }
        return restored

    async def export_snapshot(self) -> dict[str, dict[str, Any]]:
        snapshot: dict[str, dict[str, Any]] = {}
        for row in await self._repo.list_all():
            snapshot[row.scheduler_key] = {
                "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
                "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
                "last_run_status": row.last_run_status,
                "interval_seconds": row.interval_seconds,
                "state_json": dict(row.state_json or {}),
            }
        return snapshot

    async def apply_snapshot(self, snapshot: dict[str, dict[str, Any]]) -> None:
        for scheduler_key, fields in snapshot.items():
            default_interval = DEFAULT_INTERVALS.get(scheduler_key, 300)
            row = await self._repo.get_or_create(
                scheduler_key,
                default_interval_seconds=int(fields.get("interval_seconds") or default_interval),
            )
            if fields.get("interval_seconds") is not None:
                row.interval_seconds = int(fields["interval_seconds"])
            if fields.get("last_run_status") is not None:
                row.last_run_status = str(fields["last_run_status"])
            if fields.get("last_run_at"):
                row.last_run_at = datetime.fromisoformat(str(fields["last_run_at"]))
            if fields.get("next_run_at"):
                row.next_run_at = datetime.fromisoformat(str(fields["next_run_at"]))
            if fields.get("state_json") is not None:
                row.state_json = dict(fields["state_json"])
            row.updated_at = datetime.now(UTC)

    async def snapshot_for_shutdown(self) -> None:
        now = datetime.now(UTC)
        for row in await self._repo.list_all():
            patch = dict(row.state_json or {})
            patch["last_shutdown_at"] = now.isoformat()
            row.state_json = patch
            row.updated_at = now
        logger.info("Scheduler runtime state checkpoint saved for shutdown")


async def sleep_until_next_run(
    scheduler_key: str,
    *,
    interval_seconds: int | None = None,
    poll_seconds: float = 5.0,
) -> bool:
    """Sleep until the scheduler's next run time. Returns False if shutdown was requested."""
    while not is_shutdown_requested():
        async with session_scope_import() as session:
            service = SchedulerRuntimeService(session)
            wait_seconds = await service.seconds_until_next_run(
                scheduler_key,
                interval_seconds=interval_seconds,
            )
            await session.commit()
        if wait_seconds <= 0:
            return True
        chunk = min(wait_seconds, poll_seconds)
        try:
            await asyncio.wait_for(_shutdown_requested.wait(), timeout=chunk)
            return False
        except TimeoutError:
            continue
    return False


def session_scope_import():
    from webstudio_backend.infrastructure.database.session import session_scope

    return session_scope()
