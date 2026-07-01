"""Permanent product model deletion with inventory cascade and sale snapshot preservation."""

from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.inventory_item_repository import InventoryItemRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import ProductModelRepository
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository
from webstudio_backend.services.sale_snapshot import SaleProductSnapshot


class ProductModelDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryItemRepository(session)
        self._sales = SaleRepository(session)
        self._product_models = ProductModelRepository(session)
        self._recorder = AuditRecorder(session)

    async def delete_product_model(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        items = await self._inventory.list_for_product_model(product_model.id)
        for item in items:
            sale = await self._sales.get_by_inventory_item_id(item.id)
            if sale is not None:
                if sale.snapshot_serial_number is None:
                    detail = await self._inventory.get_detail(item.id)
                    if detail is not None:
                        SaleProductSnapshot.from_detail(detail).apply_to(sale)
                sale.inventory_item_id = None

        await self._session.flush()

        for item in items:
            await self._session.execute(
                update(AuditLog)
                .where(AuditLog.inventory_item_id == item.id)
                .values(inventory_item_id=None),
            )
        await self._session.flush()

        for item in items:
            await self._inventory.force_delete(item)

        await self._product_models.force_delete(product_model)
        await self._recorder.record_product_model_delete(product_model, actor=actor)

    async def delete_all_for_brand(self, brand_id: int, *, actor: AuditActor) -> int:
        models = await self._product_models.list_all_for_brand(brand_id)
        for product_model in models:
            await self.delete_product_model(product_model, actor=actor)
        return len(models)
