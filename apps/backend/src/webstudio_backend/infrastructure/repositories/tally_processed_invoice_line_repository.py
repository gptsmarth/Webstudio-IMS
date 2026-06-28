"""Tally processed invoice line repository."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallyLineOutcome, TallyLineStatus
from webstudio_backend.infrastructure.database.models.tally_processed_invoice_line import TallyProcessedInvoiceLine
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallyProcessedInvoiceLineRepository(SqlAlchemyRepository[TallyProcessedInvoiceLine]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallyProcessedInvoiceLine)

    async def get_line(self, invoice_id: int, line_index: int) -> TallyProcessedInvoiceLine | None:
        statement = select(TallyProcessedInvoiceLine).where(
            TallyProcessedInvoiceLine.tally_processed_invoice_id == invoice_id,
            TallyProcessedInvoiceLine.line_index == line_index,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_line(
        self,
        *,
        invoice_id: int,
        line_index: int,
        serial_number: str | None,
        stock_item_name: str | None,
    ) -> TallyProcessedInvoiceLine:
        existing = await self.get_line(invoice_id, line_index)
        if existing is not None:
            return existing
        return await self.add(
            TallyProcessedInvoiceLine(
                tally_processed_invoice_id=invoice_id,
                line_index=line_index,
                serial_number=serial_number,
                stock_item_name=stock_item_name,
                line_status=TallyLineStatus.PENDING,
            ),
        )

    async def complete_line(
        self,
        line: TallyProcessedInvoiceLine,
        *,
        outcome: TallyLineOutcome,
        inventory_item_id: uuid.UUID | None = None,
        error_message: str | None = None,
    ) -> TallyProcessedInvoiceLine:
        line.line_status = TallyLineStatus.COMPLETED
        line.line_outcome = outcome
        line.inventory_item_id = inventory_item_id
        line.error_message = error_message
        line.completed_at = datetime.now(UTC)
        await self._session.flush()
        return line

    async def fail_line(
        self,
        line: TallyProcessedInvoiceLine,
        *,
        outcome: TallyLineOutcome,
        error_message: str | None = None,
    ) -> TallyProcessedInvoiceLine:
        line.line_status = TallyLineStatus.FAILED
        line.line_outcome = outcome
        line.error_message = error_message
        line.completed_at = datetime.now(UTC)
        await self._session.flush()
        return line

    async def list_for_invoice(self, invoice_id: int) -> list[TallyProcessedInvoiceLine]:
        statement = (
            select(TallyProcessedInvoiceLine)
            .where(TallyProcessedInvoiceLine.tally_processed_invoice_id == invoice_id)
            .order_by(TallyProcessedInvoiceLine.line_index.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
