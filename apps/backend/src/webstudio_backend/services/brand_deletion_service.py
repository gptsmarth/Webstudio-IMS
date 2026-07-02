"""Permanent brand deletion with dependency validation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.catalogue_deletion import BrandDeletePreviewResponse
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import BrandHasDependenciesError


class BrandDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._brands = BrandRepository(session)
        self._recorder = AuditRecorder(session)

    async def preview(self, brand: Brand) -> BrandDeletePreviewResponse:
        product_model_count = await self._brands.count_product_models(brand.id)
        inventory_count = await self._brands.count_inventory_references(brand.id)
        return BrandDeletePreviewResponse(
            product_model_count=product_model_count,
            inventory_count=inventory_count,
            can_delete=product_model_count == 0 and inventory_count == 0,
        )

    async def delete_brand(self, brand: Brand, *, actor: AuditActor) -> None:
        preview = await self.preview(brand)
        if not preview.can_delete:
            raise BrandHasDependenciesError(
                brand.id,
                product_model_count=preview.product_model_count,
                inventory_count=preview.inventory_count,
            )
        await self._recorder.record_brand_delete(brand, actor=actor)
        await self._brands.force_delete(brand)
