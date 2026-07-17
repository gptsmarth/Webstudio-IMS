"""Brand persistence repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name


class BrandRepository(SqlAlchemyRepository[Brand]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Brand)

    async def get_by_name(self, name: str) -> Brand | None:
        from sqlalchemy import func

        normalized = name.strip().lower()
        statement = select(Brand).where(func.lower(Brand.name) == normalized)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        *,
        short_name: str | None = None,
        logo_filename: str | None = None,
        display_order: int = 0,
        is_active: bool = True,
        allow_duplicate_serials: bool = False,
        actor: AuditActor | None = None,
    ) -> Brand:
        normalized = normalize_required_name(name)
        if await self.get_by_name(normalized) is not None:
            raise DuplicateNameError("Brand", normalized)
        brand = await self.add(
            Brand(
                name=normalized,
                short_name=short_name.strip() if short_name else None,
                logo_filename=logo_filename.strip() if logo_filename else None,
                display_order=display_order,
                is_active=is_active,
                allow_duplicate_serials=allow_duplicate_serials,
            )
        )
        await AuditRecorder(self._session).record_brand_create(
            brand,
            actor=actor or AuditActor.system(),
        )
        return brand

    async def update(
        self,
        brand: Brand,
        *,
        name: str | None = None,
        short_name: str | None = None,
        logo_filename: str | None = None,
        display_order: int | None = None,
        is_active: bool | None = None,
        allow_duplicate_serials: bool | None = None,
        actor: AuditActor | None = None,
    ) -> Brand:
        audit_actor = actor or AuditActor.system()
        recorder = AuditRecorder(self._session)

        if name is not None:
            normalized = normalize_required_name(name)
            existing = await self.get_by_name(normalized)
            if existing is not None and existing.id != brand.id:
                raise DuplicateNameError("Brand", normalized)
            old_name = brand.name
            if normalized != old_name:
                brand.name = normalized
                await recorder.record_brand_update(
                    brand,
                    field_name="name",
                    old_value={"name": old_name},
                    new_value={"name": normalized},
                    actor=audit_actor,
                )

        if short_name is not None:
            old_val = brand.short_name
            normalized = short_name.strip() if short_name.strip() else None
            if normalized != old_val:
                brand.short_name = normalized
                await recorder.record_brand_update(
                    brand,
                    field_name="short_name",
                    old_value={"short_name": old_val},
                    new_value={"short_name": normalized},
                    actor=audit_actor,
                )

        if logo_filename is not None:
            old_val = brand.logo_filename
            normalized = logo_filename.strip() if logo_filename.strip() else None
            if normalized != old_val:
                brand.logo_filename = normalized
                await recorder.record_brand_update(
                    brand,
                    field_name="logo_filename",
                    old_value={"logo_filename": old_val},
                    new_value={"logo_filename": normalized},
                    actor=audit_actor,
                )

        if display_order is not None:
            old_val = brand.display_order
            if display_order != old_val:
                brand.display_order = display_order
                await recorder.record_brand_update(
                    brand,
                    field_name="display_order",
                    old_value={"display_order": old_val},
                    new_value={"display_order": display_order},
                    actor=audit_actor,
                )

        if allow_duplicate_serials is not None:
            old_val = brand.allow_duplicate_serials
            if allow_duplicate_serials != old_val:
                brand.allow_duplicate_serials = allow_duplicate_serials
                await recorder.record_brand_update(
                    brand,
                    field_name="allow_duplicate_serials",
                    old_value={"allow_duplicate_serials": old_val},
                    new_value={"allow_duplicate_serials": allow_duplicate_serials},
                    actor=audit_actor,
                )

        if is_active is not None:
            old_val = brand.is_active
            if is_active != old_val:
                brand.is_active = is_active
                from webstudio_backend.infrastructure.database.enums import AuditAction

                action = AuditAction.ARCHIVE if not is_active else AuditAction.RESTORE
                await recorder.record(
                    entity_type="brand",
                    entity_id=str(brand.id),
                    action=action,
                    actor=audit_actor,
                    field_name="is_active",
                    old_value={"is_active": old_val},
                    new_value={"is_active": is_active},
                    description=f"Brand '{brand.name}' {'archived' if not is_active else 'restored'}",
                )

        await self._session.flush()
        await self._session.refresh(brand)
        return brand

    async def update_name(
        self,
        brand: Brand,
        name: str,
        *,
        actor: AuditActor | None = None,
    ) -> Brand:
        return await self.update(brand, name=name, actor=actor)

    async def count_product_models(self, brand_id: int) -> int:
        statement = (
            select(func.count()).select_from(ProductModel).where(ProductModel.brand_id == brand_id)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def count_inventory_references(self, brand_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(InventoryItem)
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .where(ProductModel.brand_id == brand_id)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def force_delete(self, brand: Brand) -> None:
        await super().delete(brand)
