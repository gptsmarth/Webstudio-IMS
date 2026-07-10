"""Tally processed invoice line repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallyLineOutcome, TallyLineStatus
from webstudio_backend.infrastructure.database.models.tally_processed_invoice_line import (
    TallyProcessedInvoiceLine,
)
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


def _to_decimal(value: str | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None


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
        serial_source: str | None = None,
        normalized_serial: str | None = None,
        quantity: str | None = None,
        rate: str | None = None,
        taxable_amount: str | None = None,
        cgst_amount: str | None = None,
        sgst_amount: str | None = None,
        igst_amount: str | None = None,
        cess_amount: str | None = None,
        line_total: str | None = None,
    ) -> TallyProcessedInvoiceLine:
        existing = await self.get_line(invoice_id, line_index)
        if existing is not None:
            return existing
        return await self.add(
            TallyProcessedInvoiceLine(
                tally_processed_invoice_id=invoice_id,
                line_index=line_index,
                serial_number=serial_number,
                serial_source=serial_source,
                normalized_serial=normalized_serial,
                stock_item_name=stock_item_name,
                quantity=quantity,
                rate=_to_decimal(rate),
                taxable_amount=_to_decimal(taxable_amount),
                cgst_amount=_to_decimal(cgst_amount),
                sgst_amount=_to_decimal(sgst_amount),
                igst_amount=_to_decimal(igst_amount),
                cess_amount=_to_decimal(cess_amount),
                line_total=_to_decimal(line_total),
                invoice_model_name=stock_item_name,
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
        match_result: str | None = None,
        decision: str | None = None,
        decision_reason: str | None = None,
        ims_model_name: str | None = None,
        sale_id: int | None = None,
        is_additional_product: bool = False,
        is_unmatched_serialized: bool = False,
        review_required: bool = False,
    ) -> TallyProcessedInvoiceLine:
        line.line_status = TallyLineStatus.COMPLETED
        line.line_outcome = outcome
        line.inventory_item_id = inventory_item_id
        line.error_message = error_message
        line.match_result = match_result
        line.decision = decision
        line.decision_reason = decision_reason
        line.ims_model_name = ims_model_name
        line.sale_id = sale_id
        line.is_additional_product = is_additional_product
        line.is_unmatched_serialized = is_unmatched_serialized
        line.review_required = review_required
        line.completed_at = datetime.now(UTC)
        await self._session.flush()
        return line

    async def fail_line(
        self,
        line: TallyProcessedInvoiceLine,
        *,
        outcome: TallyLineOutcome,
        error_message: str | None = None,
        match_result: str | None = None,
        decision: str | None = None,
        decision_reason: str | None = None,
        review_required: bool = False,
    ) -> TallyProcessedInvoiceLine:
        line.line_status = TallyLineStatus.FAILED
        line.line_outcome = outcome
        line.error_message = error_message
        line.match_result = match_result
        line.decision = decision
        line.decision_reason = decision_reason
        line.review_required = review_required
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

    async def list_additional_products_for_guid(
        self,
        voucher_guid: str,
    ) -> list[TallyProcessedInvoiceLine]:
        from webstudio_backend.infrastructure.database.models.tally_processed_invoice import (
            TallyProcessedInvoice,
        )

        statement = (
            select(TallyProcessedInvoiceLine)
            .join(
                TallyProcessedInvoice,
                TallyProcessedInvoice.id == TallyProcessedInvoiceLine.tally_processed_invoice_id,
            )
            .where(TallyProcessedInvoice.tally_voucher_guid == voucher_guid)
            .where(TallyProcessedInvoiceLine.is_additional_product.is_(True))
            .order_by(TallyProcessedInvoiceLine.line_index.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_unmatched_serialized_for_guid(
        self,
        voucher_guid: str,
    ) -> list[TallyProcessedInvoiceLine]:
        from webstudio_backend.infrastructure.database.models.tally_processed_invoice import (
            TallyProcessedInvoice,
        )

        statement = (
            select(TallyProcessedInvoiceLine)
            .join(
                TallyProcessedInvoice,
                TallyProcessedInvoice.id == TallyProcessedInvoiceLine.tally_processed_invoice_id,
            )
            .where(TallyProcessedInvoice.tally_voucher_guid == voucher_guid)
            .where(TallyProcessedInvoiceLine.is_unmatched_serialized.is_(True))
            .order_by(TallyProcessedInvoiceLine.line_index.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_tracked_sale_lines_for_guid(
        self,
        voucher_guid: str,
    ) -> list[TallyProcessedInvoiceLine]:
        """Lines that produced inventory sales (Case A/B)."""
        from webstudio_backend.infrastructure.database.models.tally_processed_invoice import (
            TallyProcessedInvoice,
        )

        statement = (
            select(TallyProcessedInvoiceLine)
            .join(
                TallyProcessedInvoice,
                TallyProcessedInvoice.id == TallyProcessedInvoiceLine.tally_processed_invoice_id,
            )
            .where(TallyProcessedInvoice.tally_voucher_guid == voucher_guid)
            .where(
                TallyProcessedInvoiceLine.line_outcome.in_(
                    (
                        TallyLineOutcome.SALE_APPLIED,
                        TallyLineOutcome.SALE_APPLIED_WITH_REVIEW,
                    )
                )
            )
            .order_by(TallyProcessedInvoiceLine.line_index.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
