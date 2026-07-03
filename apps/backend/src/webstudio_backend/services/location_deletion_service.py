"""Permanent location deletion with inventory transfer."""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.catalogue_deletion import LocationDeletePreviewResponse
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.exceptions import (
    LocationHasInventoryError,
    LocationNotFoundError,
    SameLocationMovementError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository


class LocationDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._locations = LocationRepository(session)
        self._inventory = InventoryItemRepository(session)
        self._recorder = AuditRecorder(session)

    async def preview(self, location: Location) -> LocationDeletePreviewResponse:
        inventory_count = await self._inventory.count_at_location(location.id)
        movable_inventory_count = await self._inventory.count_movable_at_location(location.id)
        return LocationDeletePreviewResponse(
            inventory_count=inventory_count,
            movable_inventory_count=movable_inventory_count,
            requires_transfer=inventory_count > 0,
        )

    async def delete_location(
        self,
        location: Location,
        *,
        transfer_to_location_id: int | None,
        actor: AuditActor,
    ) -> None:
        preview = await self.preview(location)
        transferred_count = 0

        if preview.requires_transfer:
            if transfer_to_location_id is None:
                raise LocationHasInventoryError(location.id, movable_count=preview.inventory_count)
            if transfer_to_location_id == location.id:
                raise SameLocationMovementError()

            destination = await self._locations.get_by_id(transfer_to_location_id)
            if destination is None:
                raise LocationNotFoundError(transfer_to_location_id)

            transferred_count = await self._inventory.transfer_all_for_location_deletion(
                location.id,
                transfer_to_location_id,
                actor=actor,
            )
            remaining = await self._inventory.count_at_location(location.id)
            if remaining > 0:
                raise LocationHasInventoryError(location.id, movable_count=remaining)

        await self._session.execute(
            update(Sale)
            .where(
                Sale.mapped_location_id == location.id,
                Sale.snapshot_location_name.is_(None),
            )
            .values(snapshot_location_name=location.name),
        )
        await self._session.flush()

        await self._recorder.record_location_delete(
            location,
            actor=actor,
            transferred_count=transferred_count,
            transfer_to_location_id=transfer_to_location_id,
        )
        await self._locations.force_delete(location)
