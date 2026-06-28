"""Sale reflection service — shared by manual API and future Tally sync."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import InventoryStatus
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.exceptions import (
    ArchivedInventoryOperationError,
    InventoryAlreadySoldError,
    InventoryNotAvailableForSaleError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemDetailRow,
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository


@dataclass(frozen=True, slots=True)
class ManualSaleResult:
    inventory: InventoryItemDetailRow
    sale: Sale


class SaleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryItemRepository(session)
        self._sales = SaleRepository(session)
        self._recorder = AuditRecorder(session)

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

        sold_at = datetime.combine(sale_date, time.min, tzinfo=timezone.utc)
        old_status = item.status
        item.status = InventoryStatus.SOLD
        await self._session.flush()

        sale = await self._sales.create_manual(
            inventory_item_id=item.id,
            sold_at=sold_at,
            invoice_number=invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            recorded_by_user_id=actor.user_id,
            notes=remarks,
            sale_amount=sale_amount,
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
