"""Enterprise rollback run persistence — permanent history, no deletes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.enterprise_rollback_run import (
    EnterpriseRollbackRun,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate


class EnterpriseRollbackRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: EnterpriseRollbackRun) -> EnterpriseRollbackRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def save(self, run: EnterpriseRollbackRun) -> EnterpriseRollbackRun:
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_by_id(self, run_id: int) -> EnterpriseRollbackRun | None:
        result = await self._session.execute(
            select(EnterpriseRollbackRun).where(EnterpriseRollbackRun.id == run_id),
        )
        return result.scalar_one_or_none()

    async def list_history(self, *, page: PageParams) -> tuple[list[EnterpriseRollbackRun], int]:
        base = select(EnterpriseRollbackRun).order_by(desc(EnterpriseRollbackRun.created_at))
        result = await paginate(self._session, base, page)
        return result.items, result.total_items

    async def count_all(self) -> int:
        value = await self._session.scalar(select(func.count()).select_from(EnterpriseRollbackRun))
        return int(value or 0)

    async def mark_step(
        self,
        run: EnterpriseRollbackRun,
        *,
        step: str,
        status: str,
        detail: dict | None = None,
        error: str | None = None,
    ) -> EnterpriseRollbackRun:
        steps = list(run.steps_json or [])
        entry: dict = {
            "step": step,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if detail:
            entry["detail"] = detail
        if error:
            entry["error"] = error
        steps.append(entry)
        run.steps_json = steps
        run.current_step = step
        return await self.save(run)
