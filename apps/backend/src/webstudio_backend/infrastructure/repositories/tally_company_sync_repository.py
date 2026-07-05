"""Tally company sync repository."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select, update
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
        return await self.add(
            TallyCompanySync(company_name=company_name, connection_status="disconnected")
        )

    async def list_active(self) -> list[TallyCompanySync]:
        statement = (
            select(TallyCompanySync)
            .where(TallyCompanySync.is_active.is_(True))
            .order_by(TallyCompanySync.company_name.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def resolve_primary(self, configured_company_name: str) -> TallyCompanySync | None:
        """Return the sync row for the configured company name, if it exists."""
        normalized = configured_company_name.strip()
        if not normalized:
            return None
        return await self.get_by_company_name(normalized)

    async def deactivate_except(self, configured_company_name: str) -> None:
        """Mark stale company rows inactive after settings change."""
        normalized = configured_company_name.strip()
        if not normalized:
            return
        statement = (
            update(TallyCompanySync)
            .where(
                TallyCompanySync.is_active.is_(True),
                TallyCompanySync.company_name != normalized,
            )
            .values(is_active=False)
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def update_sync_state(
        self,
        company_sync: TallyCompanySync,
        *,
        last_successful_sync_at: datetime | None = None,
        last_processed_guid: str | None = None,
        last_processed_master_id: str | None = None,
        last_error: str | None = None,
        connection_status: str | None = None,
        connectivity_status: str | None = None,
        last_successful_connection_at: datetime | None = None,
        last_failed_connection_at: datetime | None = None,
        last_resolved_ip: str | None = None,
        last_imported_voucher_date: date | None = None,
        consecutive_sync_failures: int | None = None,
        sync_in_progress: bool | None = None,
        last_sync_duration_ms: int | None = None,
        last_invoices_imported_count: int | None = None,
        clear_last_error: bool = False,
    ) -> TallyCompanySync:
        if last_successful_sync_at is not None:
            company_sync.last_successful_sync_at = last_successful_sync_at
        if last_processed_guid is not None:
            company_sync.last_processed_guid = last_processed_guid
        if last_processed_master_id is not None:
            company_sync.last_processed_master_id = last_processed_master_id
        if clear_last_error:
            company_sync.last_error = ""
        elif last_error is not None:
            company_sync.last_error = last_error
        if connection_status is not None:
            company_sync.connection_status = connection_status
        if connectivity_status is not None:
            company_sync.connectivity_status = connectivity_status
        if last_successful_connection_at is not None:
            company_sync.last_successful_connection_at = last_successful_connection_at
        if last_failed_connection_at is not None:
            company_sync.last_failed_connection_at = last_failed_connection_at
        if last_resolved_ip is not None:
            company_sync.last_resolved_ip = last_resolved_ip
        if last_imported_voucher_date is not None:
            company_sync.last_imported_voucher_date = last_imported_voucher_date
        if consecutive_sync_failures is not None:
            company_sync.consecutive_sync_failures = consecutive_sync_failures
        if sync_in_progress is not None:
            company_sync.sync_in_progress = sync_in_progress
        if last_sync_duration_ms is not None:
            company_sync.last_sync_duration_ms = last_sync_duration_ms
        if last_invoices_imported_count is not None:
            company_sync.last_invoices_imported_count = last_invoices_imported_count
        await self._session.flush()
        return company_sync

    async def clear_all_sync_in_progress(self) -> None:
        statement = (
            update(TallyCompanySync)
            .where(TallyCompanySync.sync_in_progress.is_(True))
            .values(sync_in_progress=False)
        )
        await self._session.execute(statement)
        await self._session.flush()
