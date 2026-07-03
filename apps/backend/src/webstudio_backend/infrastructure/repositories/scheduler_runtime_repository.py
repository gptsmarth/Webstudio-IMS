"""Scheduler runtime state persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.scheduler_runtime_state import SchedulerRuntimeState


class SchedulerRuntimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, scheduler_key: str) -> SchedulerRuntimeState | None:
        result = await self._session.execute(
            select(SchedulerRuntimeState).where(SchedulerRuntimeState.scheduler_key == scheduler_key),
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, scheduler_key: str, *, default_interval_seconds: int) -> SchedulerRuntimeState:
        row = await self.get(scheduler_key)
        if row is not None:
            return row
        row = SchedulerRuntimeState(
            scheduler_key=scheduler_key,
            interval_seconds=default_interval_seconds,
            state_json={},
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update_run(
        self,
        scheduler_key: str,
        *,
        last_run_at: datetime,
        last_run_status: str,
        next_run_at: datetime | None,
        state_json: dict[str, Any] | None = None,
    ) -> SchedulerRuntimeState:
        row = await self.get(scheduler_key)
        if row is None:
            raise KeyError(f"Unknown scheduler key: {scheduler_key}")
        row.last_run_at = last_run_at
        row.last_run_status = last_run_status
        row.next_run_at = next_run_at
        row.updated_at = datetime.now(UTC)
        if state_json is not None:
            row.state_json = state_json
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def merge_state_json(self, scheduler_key: str, patch: dict[str, Any]) -> SchedulerRuntimeState:
        row = await self.get(scheduler_key)
        if row is None:
            raise KeyError(f"Unknown scheduler key: {scheduler_key}")
        merged = dict(row.state_json or {})
        merged.update(patch)
        row.state_json = merged
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_all(self) -> list[SchedulerRuntimeState]:
        result = await self._session.execute(select(SchedulerRuntimeState))
        return list(result.scalars().all())
