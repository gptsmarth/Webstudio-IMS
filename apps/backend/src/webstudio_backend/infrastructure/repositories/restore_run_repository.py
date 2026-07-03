"""Restore run persistence repository."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.restore_run import RestoreRun
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


@dataclass(frozen=True, slots=True)
class RestoreRunSnapshot:
    """Captured before entire_database restore — the row may be wiped by pg_restore."""

    id: int
    filename: str
    source: str
    restore_scope: str
    actor_user_id: int | None
    actor_display_name: str | None


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
        run: RestoreRun | RestoreRunSnapshot,
        *,
        emergency_backup_filename: str | None,
        duration_ms: int,
        verification_status: str,
        warnings: list[str],
        errors: list[str],
    ) -> RestoreRun:
        if isinstance(run, RestoreRunSnapshot):
            snapshot = run
        else:
            snapshot = RestoreRunSnapshot(
                id=run.id,
                filename=run.filename,
                source=run.source,
                restore_scope=run.restore_scope,
                actor_user_id=run.actor_user_id,
                actor_display_name=run.actor_display_name,
            )

        status = "completed" if not errors else "failed"
        completed_at = datetime.now(UTC)
        warnings_json = json.dumps(warnings)
        errors_json = json.dumps(errors)

        result = await self._session.execute(
            select(RestoreRun).where(RestoreRun.id == snapshot.id).with_for_update(),
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            # entire_database restore replaces table data; re-insert completion record.
            return await self.add(
                RestoreRun(
                    filename=snapshot.filename,
                    source=snapshot.source,
                    restore_scope=snapshot.restore_scope,
                    status=status,
                    verification_status=verification_status,
                    emergency_backup_filename=emergency_backup_filename,
                    duration_ms=duration_ms,
                    actor_user_id=snapshot.actor_user_id,
                    actor_display_name=snapshot.actor_display_name,
                    warnings_json=warnings_json,
                    errors_json=errors_json,
                    completed_at=completed_at,
                ),
            )

        existing.status = status
        existing.emergency_backup_filename = emergency_backup_filename
        existing.duration_ms = duration_ms
        existing.verification_status = verification_status
        existing.warnings_json = warnings_json
        existing.errors_json = errors_json
        existing.completed_at = completed_at
        await self._session.flush()
        await self._session.refresh(existing)
        return existing
