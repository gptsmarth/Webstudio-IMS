"""Location persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import LocationType
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name


class LocationRepository(SqlAlchemyRepository[Location]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Location)

    async def get_by_name(self, name: str) -> Location | None:
        from sqlalchemy import func
        normalized = name.strip().lower()
        statement = select(Location).where(func.lower(Location.name) == normalized)
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
        actor: AuditActor | None = None,
    ) -> Location:
        normalized = normalize_required_name(name)
        if await self.get_by_name(normalized) is not None:
            raise DuplicateNameError("Location", normalized)
        location = await self.add(
            Location(
                name=normalized,
                location_type=location_type,
                is_active=is_active,
                sort_order=sort_order,
                branch_id=branch_id,
            ),
        )
        await AuditRecorder(self._session).record_location_create(
            location,
            actor=actor or AuditActor.system(),
        )
        return location

    async def update(
        self,
        location: Location,
        *,
        name: str | None = None,
        location_type: LocationType | None = None,
        is_active: bool | None = None,
        sort_order: int | None = None,
        branch_id: int | None = None,
        actor: AuditActor | None = None,
    ) -> Location:
        audit_actor = actor or AuditActor.system()
        recorder = AuditRecorder(self._session)

        if name is not None:
            normalized = normalize_required_name(name)
            existing = await self.get_by_name(normalized)
            if existing is not None and existing.id != location.id:
                raise DuplicateNameError("Location", normalized)
            old_name = location.name
            if normalized != old_name:
                location.name = normalized
                await recorder.record_location_update(
                    location,
                    field_name="name",
                    old_value={"name": old_name},
                    new_value={"name": normalized},
                    actor=audit_actor,
                )

        if location_type is not None:
            old_val = location.location_type
            if location_type != old_val:
                location.location_type = location_type
                await recorder.record_location_update(
                    location,
                    field_name="location_type",
                    old_value={"location_type": old_val.value},
                    new_value={"location_type": location_type.value},
                    actor=audit_actor,
                )

        if sort_order is not None:
            old_val = location.sort_order
            if sort_order != old_val:
                location.sort_order = sort_order
                await recorder.record_location_update(
                    location,
                    field_name="sort_order",
                    old_value={"sort_order": old_val},
                    new_value={"sort_order": sort_order},
                    actor=audit_actor,
                )

        if branch_id is not None:
            old_val = location.branch_id
            if branch_id != old_val:
                location.branch_id = branch_id
                await recorder.record_location_update(
                    location,
                    field_name="branch_id",
                    old_value={"branch_id": old_val},
                    new_value={"branch_id": branch_id},
                    actor=audit_actor,
                )

        if is_active is not None:
            old_val = location.is_active
            if is_active != old_val:
                location.is_active = is_active
                from webstudio_backend.infrastructure.database.enums import AuditAction
                action = AuditAction.ARCHIVE if not is_active else AuditAction.RESTORE
                await recorder.record(
                    entity_type="location",
                    entity_id=str(location.id),
                    action=action,
                    actor=audit_actor,
                    field_name="is_active",
                    old_value={"is_active": old_val},
                    new_value={"is_active": is_active},
                    description=f"Location '{location.name}' {'archived' if not is_active else 'restored'}",
                )

        await self._session.flush()
        await self._session.refresh(location)
        return location

    async def update_name(
        self,
        location: Location,
        name: str,
        *,
        actor: AuditActor | None = None,
    ) -> Location:
        return await self.update(location, name=name, actor=actor)
