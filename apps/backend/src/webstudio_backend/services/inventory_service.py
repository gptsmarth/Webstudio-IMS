"""Inventory business logic service."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import InventoryStatus
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam
from webstudio_backend.infrastructure.repositories.inventory_item_filters import InventorySearchFilters
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemDetailRow,
    InventoryItemRepository,
)
from webstudio_backend.services.sale_service import ManualSaleResult, SaleService


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InventoryItemRepository(session)

    async def list_items(
        self,
        filters: InventorySearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItemDetailRow]:
        return await self._repo.search(filters, page_params, sort_params)

    async def get_item(self, item_id: uuid.UUID) -> InventoryItemDetailRow | None:
        return await self._repo.get_detail(item_id)

    async def get_by_serial(self, serial_number: str) -> InventoryItemDetailRow | None:
        return await self._repo.get_detail_by_serial(serial_number)

    async def create_item(
        self,
        *,
        serial_number: str,
        product_model_id: uuid.UUID,
        color: str,
        current_location_id: int,
        status: InventoryStatus,
        purchase_date: date | None = None,
        actor: AuditActor,
    ) -> InventoryItemDetailRow:
        item = await self._repo.create(
            serial_number=serial_number,
            product_model_id=product_model_id,
            color=color,
            current_location_id=current_location_id,
            status=status,
            purchase_date=purchase_date,
            actor=actor,
        )
        detail = await self._repo.get_detail(item.id)
        assert detail is not None
        return detail

    async def update_item(
        self,
        item_id: uuid.UUID,
        *,
        actor: AuditActor,
        serial_number: str | None = None,
        product_model_id: uuid.UUID | None = None,
        color: str | None = None,
        status: InventoryStatus | None = None,
        purchase_date: date | None = None,
        set_purchase_date: bool = False,
    ) -> InventoryItemDetailRow:
        item = await self._repo.require_by_id(item_id)
        await self._repo.update(
            item,
            serial_number=serial_number,
            product_model_id=product_model_id,
            color=color,
            status=status,
            purchase_date=purchase_date,
            set_purchase_date=set_purchase_date,
            actor=actor,
        )
        detail = await self._repo.get_detail(item_id)
        assert detail is not None
        return detail

    async def archive_item(self, item_id: uuid.UUID, *, actor: AuditActor) -> InventoryItemDetailRow:
        item = await self._repo.require_by_id(item_id)
        await self._repo.archive(item, actor=actor)
        detail = await self._repo.get_detail(item_id)
        assert detail is not None
        return detail

    async def restore_item(self, item_id: uuid.UUID, *, actor: AuditActor) -> InventoryItemDetailRow:
        item = await self._repo.require_by_id(item_id)
        await self._repo.restore(item, actor=actor)
        detail = await self._repo.get_detail(item_id)
        assert detail is not None
        return detail

    async def transfer_location(
        self,
        item_id: uuid.UUID,
        *,
        to_location_id: int,
        actor: AuditActor,
    ) -> InventoryItemDetailRow:
        item = await self._repo.require_by_id(item_id)
        await self._repo.transfer_location(item, to_location_id=to_location_id, actor=actor)
        detail = await self._repo.get_detail(item_id)
        assert detail is not None
        return detail

    async def mark_as_sold(
        self,
        item_id: uuid.UUID,
        *,
        invoice_number: str,
        customer_name: str,
        payment_mode: str,
        sale_date: date,
        remarks: str | None,
        sale_amount: float | None = None,
        actor: AuditActor,
    ) -> ManualSaleResult:
        return await SaleService(self._session).reflect_manual_sale(
            item_id,
            invoice_number=invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            sale_date=sale_date,
            remarks=remarks,
            sale_amount=sale_amount,
            actor=actor,
        )
