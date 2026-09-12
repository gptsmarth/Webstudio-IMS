"""Sale reflection service — shared by manual API and future Tally sync."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import InventoryStatus, TallyProcessingStatus
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.exceptions import (
    ArchivedInventoryOperationError,
    InventoryAlreadySoldError,
    InventoryNotAvailableForSaleError,
    SaleAlreadyCancelledError,
    SaleCancelNotAllowedError,
    SaleNotFoundError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemDetailRow,
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.services.sale_snapshot import SaleProductSnapshot


@dataclass(frozen=True, slots=True)
class ManualSaleResult:
    inventory: InventoryItemDetailRow
    sale: Sale


@dataclass(frozen=True, slots=True)
class CancelSaleResult:
    inventory: InventoryItemDetailRow
    sale: Sale
    restored_serial_number: str


class SaleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryItemRepository(session)
        self._sales = SaleRepository(session)
        self._recorder = AuditRecorder(session)
        self._processed_invoices = TallyProcessedInvoiceRepository(session)
        self._processed_lines = TallyProcessedInvoiceLineRepository(session)

    async def reflect_manual_sale(
        self,
        inventory_item_id: uuid.UUID,
        *,
        invoice_number: str,
        customer_name: str,
        payment_mode: str,
        sale_date: date,
        remarks: str | None,
        sale_amount: float | None = None,
        actor: AuditActor,
    ) -> ManualSaleResult:
        if actor.user_id is None:
            raise ValueError("Manual sale requires an authenticated user")

        item = await self._inventory.require_by_id(inventory_item_id)
        if item.is_archived:
            raise ArchivedInventoryOperationError(str(item.id), "sold")
        if item.status is InventoryStatus.SOLD:
            raise InventoryAlreadySoldError(str(item.id))
        if item.status is not InventoryStatus.AVAILABLE:
            raise InventoryNotAvailableForSaleError(str(item.id), item.status.value)

        sold_at = datetime.combine(sale_date, time.min, tzinfo=UTC)
        old_status = item.status
        item.status = InventoryStatus.SOLD
        await self._session.flush()

        detail = await self._inventory.get_detail(item.id)
        assert detail is not None
        snapshot = SaleProductSnapshot.from_detail(detail)

        sale = await self._sales.create_manual(
            inventory_item_id=item.id,
            sold_at=sold_at,
            invoice_number=invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            recorded_by_user_id=actor.user_id,
            notes=remarks,
            sale_amount=sale_amount,
            snapshot=snapshot,
            actor=actor,
        )

        await self._recorder.record_inventory_status_change(
            item,
            old_status=old_status,
            new_status=InventoryStatus.SOLD,
            actor=actor,
            extra_new_value={
                "invoice_number": sale.invoice_number,
                "customer_name": sale.customer_name,
                "payment_mode": sale.payment_mode,
                "sale_id": sale.id,
            },
        )

        detail = await self._inventory.get_detail(item.id)
        assert detail is not None
        return ManualSaleResult(inventory=detail, sale=sale)

    async def cancel_sale(
        self,
        sale_id: int,
        *,
        reason: str | None,
        actor: AuditActor,
    ) -> CancelSaleResult:
        if actor.user_id is None:
            raise ValueError("Sale cancellation requires an authenticated user")

        sale = await self._sales.get_by_id(sale_id)
        if sale is None or sale.cancelled_at is not None:
            if sale is not None and sale.cancelled_at is not None:
                raise SaleAlreadyCancelledError(sale_id)
            raise SaleNotFoundError(sale_id)

        if sale.inventory_item_id is None:
            raise SaleCancelNotAllowedError(
                "Cannot restore stock — inventory item is no longer linked to this sale.",
            )

        item = await self._inventory.require_by_id(sale.inventory_item_id)
        if item.is_archived:
            raise SaleCancelNotAllowedError(
                "Cannot cancel sale — linked inventory item is archived.",
            )
        if item.status is not InventoryStatus.SOLD:
            raise SaleCancelNotAllowedError(
                f"Cannot cancel sale — inventory item status is {item.status.value}, not sold.",
            )

        linked_sale = await self._sales.get_by_inventory_item_id(item.id)
        if linked_sale is None or linked_sale.id != sale.id:
            raise SaleCancelNotAllowedError(
                "Cannot cancel sale — inventory item is not linked to this active sale.",
            )

        restored_serial = item.serial_number
        old_status = item.status
        item.status = InventoryStatus.AVAILABLE
        await self._session.flush()

        inventory_item_id = sale.inventory_item_id
        sale.inventory_item_id = None
        sale.cancelled_at = datetime.now(UTC)
        sale.cancelled_by_user_id = actor.user_id
        sale.cancellation_reason = reason.strip() if reason and reason.strip() else None
        await self._session.flush()

        await self._recorder.record_inventory_status_change(
            item,
            old_status=old_status,
            new_status=InventoryStatus.AVAILABLE,
            actor=actor,
            extra_new_value={
                "invoice_number": sale.invoice_number,
                "sale_id": sale.id,
                "cancelled": True,
            },
        )
        await self._recorder.record_sale_cancel(
            sale,
            inventory_item_id=inventory_item_id,
            restored_serial_number=restored_serial,
            actor=actor,
        )

        # A sale created by Tally sync leaves its invoice line marked
        # "completed" — that's what makes a later sync/backfill treat the
        # invoice as already fully processed and skip it forever. Reset the
        # line (and its parent invoice's terminal status) so the unit can be
        # correctly re-matched and re-sold if it's still genuinely billed in
        # Tally. Sales entered manually have no such line to reset.
        processed_lines = await self._processed_lines.list_by_sale_id(sale.id)
        reset_invoice_ids: set[int] = set()
        for line in processed_lines:
            await self._processed_lines.reset_line_after_sale_cancelled(line)
            reset_invoice_ids.add(line.tally_processed_invoice_id)
        for invoice_id in reset_invoice_ids:
            invoice = await self._processed_invoices.get_by_id(invoice_id)
            if invoice is not None:
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.FAILED)

        detail = await self._inventory.get_detail(item.id)
        assert detail is not None
        return CancelSaleResult(
            inventory=detail,
            sale=sale,
            restored_serial_number=restored_serial,
        )
