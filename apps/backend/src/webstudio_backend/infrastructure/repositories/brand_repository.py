"""Brand persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name


class BrandRepository(SqlAlchemyRepository[Brand]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Brand)

    async def get_by_name(self, name: str) -> Brand | None:
        normalized = name.strip()
        statement = select(Brand).where(Brand.name == normalized)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        *,
        is_active: bool = True,
        actor: AuditActor | None = None,
    ) -> Brand:
        normalized = normalize_required_name(name)
        if await self.get_by_name(normalized) is not None:
            raise DuplicateNameError("Brand", normalized)
        brand = await self.add(Brand(name=normalized, is_active=is_active))
        await AuditRecorder(self._session).record_brand_create(
            brand,
            actor=actor or AuditActor.system(),
        )
        return brand

    async def update_name(
        self,
        brand: Brand,
        name: str,
        *,
        actor: AuditActor | None = None,
    ) -> Brand:
        normalized = normalize_required_name(name)
        existing = await self.get_by_name(normalized)
        if existing is not None and existing.id != brand.id:
            raise DuplicateNameError("Brand", normalized)
        old_name = brand.name
        brand.name = normalized
        await self._session.flush()
        await self._session.refresh(brand)
        await AuditRecorder(self._session).record_brand_update(
            brand,
            field_name="name",
            old_value={"name": old_name},
            new_value={"name": normalized},
            actor=actor or AuditActor.system(),
        )
        return brand
