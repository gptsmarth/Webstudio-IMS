"""Backup run persistence repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.backup_run import BackupRun
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.repositories.backup_run_filters import BackupHistoryFilters


class BackupRunRepository(SqlAlchemyRepository[BackupRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BackupRun)

    async def create_run(
        self,
        *,
        filename: str,
        archive_path: str,
        backup_type: str,
        trigger_type: str,
        storage_backend: str,
        creator_user_id: int | None,
        creator_display_name: str | None,
        base_backup_id: int | None = None,
    ) -> BackupRun:
        return await self.add(
            BackupRun(
                filename=filename,
                archive_path=archive_path,
                backup_type=backup_type,
                trigger_type=trigger_type,
                storage_backend=storage_backend,
                status="running",
                verification_status="pending",
                creator_user_id=creator_user_id,
                creator_display_name=creator_display_name,
                base_backup_id=base_backup_id,
            ),
        )

    async def list_recent(
        self, *, limit: int = 50, include_archived: bool = True
    ) -> list[BackupRun]:
        statement = select(BackupRun).order_by(BackupRun.created_at.desc()).limit(limit)
        if not include_archived:
            statement = statement.where(BackupRun.is_archived.is_(False))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def search(
        self,
        filters: BackupHistoryFilters,
        page_params: PageParams,
    ) -> PageResult[BackupRun]:
        statement = select(BackupRun)
        if not filters.include_archived:
            statement = statement.where(BackupRun.is_archived.is_(False))
        if filters.date_from is not None:
            statement = statement.where(BackupRun.created_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(BackupRun.created_at <= filters.date_to)
        if filters.backup_type:
            statement = statement.where(BackupRun.backup_type == filters.backup_type)
        if filters.trigger_type:
            statement = statement.where(BackupRun.trigger_type == filters.trigger_type)
        if filters.creator:
            pattern = f"%{filters.creator.strip()}%"
            statement = statement.where(
                or_(
                    BackupRun.creator_display_name.ilike(pattern),
                ),
            )
        if filters.status:
            if filters.status == "archived":
                statement = statement.where(BackupRun.is_archived.is_(True))
            else:
                statement = statement.where(
                    BackupRun.status == filters.status,
                    BackupRun.is_archived.is_(False),
                )
        statement = statement.order_by(BackupRun.created_at.desc())
        return await paginate(self._session, statement, page_params)

    async def count_summary(self) -> dict[str, int]:
        result = await self._session.execute(
            select(
                func.count(BackupRun.id),
                func.count(BackupRun.id).filter(BackupRun.status == "failed"),
                func.count(BackupRun.id).filter(BackupRun.verification_status == "warning"),
                func.count(BackupRun.id).filter(BackupRun.is_archived.is_(True)),
            ),
        )
        total, failed, warnings, archived = result.one()
        return {
            "total": int(total or 0),
            "failed": int(failed or 0),
            "warnings": int(warnings or 0),
            "archived": int(archived or 0),
        }

    async def oldest_and_newest(self) -> tuple[datetime | None, datetime | None]:
        oldest = await self._session.execute(
            select(BackupRun.created_at).order_by(BackupRun.created_at.asc()).limit(1),
        )
        newest = await self._session.execute(
            select(BackupRun.created_at).order_by(BackupRun.created_at.desc()).limit(1),
        )
        return oldest.scalar_one_or_none(), newest.scalar_one_or_none()

    async def mark_archived(self, run: BackupRun) -> BackupRun:
        run.is_archived = True
        run.status = "archived"
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def delete_run(self, run: BackupRun) -> None:
        await self._session.delete(run)
        await self._session.flush()

    async def get_by_filename(self, filename: str) -> BackupRun | None:
        result = await self._session.execute(
            select(BackupRun).where(BackupRun.filename == filename).limit(1),
        )
        return result.scalar_one_or_none()

    async def mark_completed(
        self,
        run: BackupRun,
        *,
        size_bytes: int,
        duration_ms: int,
        checksum_sha256: str,
        schema_version: str,
        app_version: str,
        verification_status: str,
        warnings: list[str],
        errors: list[str],
        manifest: dict,
    ) -> BackupRun:
        run.status = "completed" if not errors else "failed"
        run.size_bytes = size_bytes
        run.duration_ms = duration_ms
        run.checksum_sha256 = checksum_sha256
        run.schema_version = schema_version
        run.app_version = app_version
        run.verification_status = verification_status
        run.warnings_json = json.dumps(warnings)
        run.errors_json = json.dumps(errors)
        run.manifest_json = json.dumps(manifest)
        run.completed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def mark_failed(self, run: BackupRun, *, errors: list[str]) -> BackupRun:
        run.status = "failed"
        run.verification_status = "failed"
        run.errors_json = json.dumps(errors)
        run.completed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(run)
        return run
