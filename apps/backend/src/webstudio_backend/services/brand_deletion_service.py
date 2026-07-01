"""Permanent brand deletion with product model cascade and sale snapshot preservation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.services.product_model_deletion_service import ProductModelDeletionService


class BrandDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._brands = BrandRepository(session)
        self._recorder = AuditRecorder(session)

    async def delete_brand(self, brand: Brand, *, actor: AuditActor) -> None:
        await ProductModelDeletionService(self._session).delete_all_for_brand(brand.id, actor=actor)
        await self._recorder.record_brand_delete(brand, actor=actor)
        await self._brands.force_delete(brand)
