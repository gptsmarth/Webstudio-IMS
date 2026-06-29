"""Restore run persistence repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.restore_run import RestoreRun
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class RestoreRunRepository(SqlAlchemyRepository[RestoreRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RestoreRun)

    async def create_run(
        self,
        *,
        filename: str,
        source: str,
        restore_scope: str,
        actor_user_id: int | None,
        actor_display_name: str | None,
    ) -> RestoreRun:
        return await self.add(
            RestoreRun(
                filename=filename,
                source=source,
                restore_scope=restore_scope,
                status="running",
                verification_status="pending",
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
            ),
        )

    async def list_recent(self, *, limit: int = 25) -> list[RestoreRun]:
        result = await self._session.execute(
            select(RestoreRun).order_by(RestoreRun.created_at.desc()).limit(limit),
        )
        return list(result.scalars().all())

    async def mark_completed(
        self,
        run: RestoreRun,
        *,
        emergency_backup_filename: str | None,
        duration_ms: int,
        verification_status: str,
        warnings: list[str],
        errors: list[str],
    ) -> RestoreRun:
        run.status = "completed" if not errors else "failed"
        run.emergency_backup_filename = emergency_backup_filename
        run.duration_ms = duration_ms
        run.verification_status = verification_status
        run.warnings_json = json.dumps(warnings)
        run.errors_json = json.dumps(errors)
        run.completed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(run)
        return run
