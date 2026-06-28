"""Tally company sync repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallyCompanySyncRepository(SqlAlchemyRepository[TallyCompanySync]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallyCompanySync)

    async def get_by_company_name(self, company_name: str) -> TallyCompanySync | None:
        statement = select(TallyCompanySync).where(TallyCompanySync.company_name == company_name)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create(self, company_name: str) -> TallyCompanySync:
        existing = await self.get_by_company_name(company_name)
        if existing is not None:
            return existing
        return await self.add(TallyCompanySync(company_name=company_name, connection_status="disconnected"))

    async def list_active(self) -> list[TallyCompanySync]:
        statement = (
            select(TallyCompanySync)
            .where(TallyCompanySync.is_active.is_(True))
            .order_by(TallyCompanySync.company_name.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def update_sync_state(
        self,
        company_sync: TallyCompanySync,
        *,
        last_successful_sync_at: datetime | None = None,
        last_processed_guid: str | None = None,
        last_processed_master_id: str | None = None,
        last_error: str | None = None,
        connection_status: str | None = None,
    ) -> TallyCompanySync:
        if last_successful_sync_at is not None:
            company_sync.last_successful_sync_at = last_successful_sync_at
        if last_processed_guid is not None:
            company_sync.last_processed_guid = last_processed_guid
        if last_processed_master_id is not None:
            company_sync.last_processed_master_id = last_processed_master_id
        if last_error is not None:
            company_sync.last_error = last_error
        if connection_status is not None:
            company_sync.connection_status = connection_status
        await self._session.flush()
        return company_sync
