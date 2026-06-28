"""Tally processed invoice repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallyProcessingStatus
from webstudio_backend.infrastructure.database.models.tally_processed_invoice import TallyProcessedInvoice
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallyProcessedInvoiceRepository(SqlAlchemyRepository[TallyProcessedInvoice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallyProcessedInvoice)

    async def find_by_guid(self, company_sync_id: int, guid: str) -> TallyProcessedInvoice | None:
        statement = select(TallyProcessedInvoice).where(
            TallyProcessedInvoice.tally_company_sync_id == company_sync_id,
            TallyProcessedInvoice.tally_voucher_guid == guid,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_master_id(self, company_sync_id: int, master_id: str) -> TallyProcessedInvoice | None:
        statement = select(TallyProcessedInvoice).where(
            TallyProcessedInvoice.tally_company_sync_id == company_sync_id,
            TallyProcessedInvoice.tally_master_id == master_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_voucher_number(
        self,
        company_sync_id: int,
        voucher_number: str,
    ) -> TallyProcessedInvoice | None:
        statement = select(TallyProcessedInvoice).where(
            TallyProcessedInvoice.tally_company_sync_id == company_sync_id,
            TallyProcessedInvoice.tally_voucher_number == voucher_number,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_pending(
        self,
        *,
        company_sync_id: int,
        guid: str,
        master_id: str | None,
        voucher_number: str,
        printed_invoice_number: str | None,
        voucher_type: str | None,
    ) -> tuple[TallyProcessedInvoice, bool]:
        existing = await self.find_by_guid(company_sync_id, guid)
        if existing is not None:
            return existing, False
        if master_id:
            by_master = await self.find_by_master_id(company_sync_id, master_id)
            if by_master is not None:
                return by_master, False
        by_number = await self.find_by_voucher_number(company_sync_id, voucher_number)
        if by_number is not None:
            return by_number, False

        now = datetime.now(UTC)
        invoice = await self.add(
            TallyProcessedInvoice(
                tally_company_sync_id=company_sync_id,
                tally_voucher_guid=guid,
                tally_master_id=master_id,
                tally_voucher_number=voucher_number,
                printed_invoice_number=printed_invoice_number,
                voucher_type=voucher_type,
                processing_status=TallyProcessingStatus.FAILED,
                first_attempt_at=now,
                last_attempt_at=now,
            ),
        )
        return invoice, True

    async def update_status(
        self,
        invoice: TallyProcessedInvoice,
        status: TallyProcessingStatus,
    ) -> TallyProcessedInvoice:
        invoice.processing_status = status
        invoice.last_attempt_at = datetime.now(UTC)
        if status is TallyProcessingStatus.SUCCESS:
            invoice.completed_at = datetime.now(UTC)
        await self._session.flush()
        return invoice
