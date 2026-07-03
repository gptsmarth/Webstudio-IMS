"""Enterprise deployment run persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.release_deployment_run import (
    ReleaseDeploymentRun,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate


class ReleaseDeploymentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: ReleaseDeploymentRun) -> ReleaseDeploymentRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def save(self, run: ReleaseDeploymentRun) -> ReleaseDeploymentRun:
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_by_id(self, run_id: int) -> ReleaseDeploymentRun | None:
        result = await self._session.execute(
            select(ReleaseDeploymentRun).where(ReleaseDeploymentRun.id == run_id),
        )
        return result.scalar_one_or_none()

    async def get_latest(self) -> ReleaseDeploymentRun | None:
        result = await self._session.execute(
            select(ReleaseDeploymentRun).order_by(desc(ReleaseDeploymentRun.created_at)).limit(1),
        )
        return result.scalar_one_or_none()

    async def list_history(self, *, page: PageParams) -> tuple[list[ReleaseDeploymentRun], int]:
        base = select(ReleaseDeploymentRun).order_by(desc(ReleaseDeploymentRun.created_at))
        result = await paginate(self._session, base, page)
        return result.items, result.total_items

    async def list_recent(self, *, limit: int = 20) -> list[ReleaseDeploymentRun]:
        result = await self._session.execute(
            select(ReleaseDeploymentRun)
            .order_by(desc(ReleaseDeploymentRun.created_at))
            .limit(limit),
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(
            select(ReleaseDeploymentRun.status, func.count()).group_by(ReleaseDeploymentRun.status),
        )
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def mark_step(
        self,
        run: ReleaseDeploymentRun,
        *,
        step: str,
        status: str,
        detail: dict | None = None,
        error: str | None = None,
    ) -> ReleaseDeploymentRun:
        steps = list(run.steps_json or [])
        entry = {
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
