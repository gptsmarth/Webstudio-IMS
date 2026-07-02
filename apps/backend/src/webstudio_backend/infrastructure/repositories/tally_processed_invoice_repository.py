"""Tally processed invoice repository."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallyProcessingStatus
from webstudio_backend.infrastructure.database.models.tally_processed_invoice import TallyProcessedInvoice
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.integrations.tally.incremental_sync import normalize_party_name, normalize_voucher_amount


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

    async def find_by_fallback_fingerprint(
        self,
        company_sync_id: int,
        *,
        voucher_date: date,
        voucher_number: str,
        amount: str | Decimal | None,
        party_name: str | None,
    ) -> TallyProcessedInvoice | None:
        normalized_amount = normalize_voucher_amount(amount)
        normalized_party = normalize_party_name(party_name)
        statement = select(TallyProcessedInvoice).where(
            TallyProcessedInvoice.tally_company_sync_id == company_sync_id,
            TallyProcessedInvoice.voucher_date == voucher_date,
            TallyProcessedInvoice.tally_voucher_number == voucher_number.strip(),
            TallyProcessedInvoice.party_name == normalized_party,
        )
        if normalized_amount is None:
            statement = statement.where(TallyProcessedInvoice.voucher_amount.is_(None))
        else:
            statement = statement.where(TallyProcessedInvoice.voucher_amount == normalized_amount)
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
        voucher_date: date | None = None,
        party_name: str | None = None,
        amount: str | Decimal | None = None,
    ) -> tuple[TallyProcessedInvoice, bool]:
        existing = await self.find_by_guid(company_sync_id, guid)
        if existing is not None:
            return existing, False

        now = datetime.now(UTC)
        invoice = await self.add(
            TallyProcessedInvoice(
                tally_company_sync_id=company_sync_id,
                tally_voucher_guid=guid,
                tally_master_id=master_id,
                tally_voucher_number=voucher_number,
                printed_invoice_number=printed_invoice_number,
                voucher_type=voucher_type,
                voucher_date=voucher_date,
                party_name=normalize_party_name(party_name) if party_name else None,
                voucher_amount=normalize_voucher_amount(amount),
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

    async def get_last_successful_import(
        self,
        company_sync_id: int,
    ) -> TallyProcessedInvoice | None:
        from webstudio_backend.infrastructure.database.enums import TallyProcessingStatus

        statement = (
            select(TallyProcessedInvoice)
            .where(
                TallyProcessedInvoice.tally_company_sync_id == company_sync_id,
                TallyProcessedInvoice.processing_status == TallyProcessingStatus.SUCCESS,
            )
            .order_by(TallyProcessedInvoice.completed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
