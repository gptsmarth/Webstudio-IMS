"""Tally synchronization run history repository."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.tally_sync_history import TallySyncHistory
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallySyncHistoryRepository(SqlAlchemyRepository[TallySyncHistory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallySyncHistory)

    async def create_started(
        self,
        *,
        company_sync_id: int,
        sync_run_id: uuid.UUID,
        correlation_id: str,
    ) -> TallySyncHistory:
        return await self.add(
            TallySyncHistory(
                tally_company_sync_id=company_sync_id,
                sync_run_id=sync_run_id,
                started_at=datetime.now(UTC),
                status="running",
                correlation_id=correlation_id,
            ),
        )

    async def finalize(
        self,
        history: TallySyncHistory,
        *,
        status: str,
        invoices_checked: int,
        invoices_imported: int,
        invoices_skipped: int,
        errors_count: int,
        error_summary: str | None = None,
    ) -> TallySyncHistory:
        completed = datetime.now(UTC)
        history.completed_at = completed
        history.duration_ms = int((completed - history.started_at).total_seconds() * 1000)
        history.status = status
        history.invoices_checked = invoices_checked
        history.invoices_imported = invoices_imported
        history.invoices_skipped = invoices_skipped
        history.errors_count = errors_count
        history.error_summary = error_summary
        await self._session.flush()
        return history

    async def get_open_for_company(self, company_sync_id: int) -> TallySyncHistory | None:
        statement = (
            select(TallySyncHistory)
            .where(
                TallySyncHistory.tally_company_sync_id == company_sync_id,
                TallySyncHistory.completed_at.is_(None),
            )
            .order_by(desc(TallySyncHistory.started_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def recent_runs(
        self,
        *,
        company_sync_id: int | None = None,
        limit: int = 20,
    ) -> list[TallySyncHistory]:
        statement = select(TallySyncHistory).order_by(desc(TallySyncHistory.started_at)).limit(limit)
        if company_sync_id is not None:
            statement = statement.where(TallySyncHistory.tally_company_sync_id == company_sync_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_runs(
        self,
        *,
        company_sync_id: int,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TallySyncHistory]:
        statement = (
            select(TallySyncHistory)
            .where(TallySyncHistory.tally_company_sync_id == company_sync_id)
            .order_by(desc(TallySyncHistory.started_at))
            .offset(offset)
            .limit(limit)
        )
        if status:
            statement = statement.where(TallySyncHistory.status == status)
        if date_from is not None:
            statement = statement.where(func.date(TallySyncHistory.started_at) >= date_from)
        if date_to is not None:
            statement = statement.where(func.date(TallySyncHistory.started_at) <= date_to)
        if search:
            needle = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    TallySyncHistory.status.ilike(needle),
                    TallySyncHistory.error_summary.ilike(needle),
                ),
            )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def sum_imported_since(
        self,
        company_sync_id: int,
        since: datetime,
    ) -> int:
        statement = select(func.coalesce(func.sum(TallySyncHistory.invoices_imported), 0)).where(
            TallySyncHistory.tally_company_sync_id == company_sync_id,
            TallySyncHistory.started_at >= since,
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def sum_total_imported(self, company_sync_id: int) -> int:
        statement = select(func.coalesce(func.sum(TallySyncHistory.invoices_imported), 0)).where(
            TallySyncHistory.tally_company_sync_id == company_sync_id,
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())
