"""Permanent product model deletion with dependency validation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.catalogue_deletion import ProductModelDeletePreviewResponse
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.exceptions import ProductModelHasInventoryError
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)


class ProductModelDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_models = ProductModelRepository(session)
        self._recorder = AuditRecorder(session)

    async def preview(self, product_model: ProductModel) -> ProductModelDeletePreviewResponse:
        inventory_count = await self._product_models.count_inventory_items(product_model.id)
        return ProductModelDeletePreviewResponse(
            inventory_count=inventory_count,
            can_delete=inventory_count == 0,
        )

    async def delete_product_model(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        preview = await self.preview(product_model)
        if not preview.can_delete:
            raise ProductModelHasInventoryError(
                str(product_model.id),
                inventory_count=preview.inventory_count,
            )
        await self._product_models.force_delete(product_model)
        await self._recorder.record_product_model_delete(product_model, actor=actor)
