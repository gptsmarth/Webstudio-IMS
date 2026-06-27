"""Location persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import LocationType
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name


class LocationRepository(SqlAlchemyRepository[Location]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Location)

    async def get_by_name(self, name: str) -> Location | None:
        normalized = name.strip()
        statement = select(Location).where(Location.name == normalized)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        *,
        location_type: LocationType,
        is_active: bool = True,
        sort_order: int | None = None,
        branch_id: int | None = None,
    ) -> Location:
        normalized = normalize_required_name(name)
        if await self.get_by_name(normalized) is not None:
            raise DuplicateNameError("Location", normalized)
        return await self.add(
            Location(
                name=normalized,
                location_type=location_type,
                is_active=is_active,
                sort_order=sort_order,
                branch_id=branch_id,
            ),
        )

    async def update_name(self, location: Location, name: str) -> Location:
        normalized = normalize_required_name(name)
        existing = await self.get_by_name(normalized)
        if existing is not None and existing.id != location.id:
            raise DuplicateNameError("Location", normalized)
        location.name = normalized
        await self._session.flush()
        await self._session.refresh(location)
        return location
