"""Automatic audit log recording for repository mutations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import AuditAction, InventoryStatus
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository


class AuditRecorder:
    """Records append-only audit entries with human-readable snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = AuditLogRepository(session)
        self._session = session

    async def record(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: AuditAction,
        actor: AuditActor,
        inventory_item_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> None:
        await self._repository.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor.user_id,
            actor_display_name=actor.display_name,
            actor_role=actor.role,
            inventory_item_id=inventory_item_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description,
        )

    async def record_brand_create(self, brand: Brand, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="brand",
            entity_id=str(brand.id),
            action=AuditAction.CREATE,
            actor=actor,
            new_value={"name": brand.name, "is_active": brand.is_active},
            description=f"Brand '{brand.name}' created",
        )

    async def record_brand_update(
        self,
        brand: Brand,
        *,
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="brand",
            entity_id=str(brand.id),
            action=AuditAction.UPDATE,
            actor=actor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=self._field_change_description(field_name, old_value, new_value),
        )

    async def record_location_create(self, location: Location, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="location",
            entity_id=str(location.id),
            action=AuditAction.CREATE,
            actor=actor,
            new_value={
                "name": location.name,
                "location_type": location.location_type.value,
                "is_active": location.is_active,
            },
            description=f"Location '{location.name}' created",
        )

    async def record_location_update(
        self,
        location: Location,
        *,
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="location",
            entity_id=str(location.id),
            action=AuditAction.UPDATE,
            actor=actor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=self._field_change_description(field_name, old_value, new_value),
        )

    async def record_product_model_create(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="product_model",
            entity_id=str(product_model.id),
            action=AuditAction.CREATE,
            actor=actor,
            new_value=await self._product_model_snapshot(product_model),
            description=(
                f"Product model '{product_model.model_name}' "
                f"({product_model.model_number}) created"
            ),
        )

    async def record_product_model_field_update(
        self,
        product_model: ProductModel,
        *,
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="product_model",
            entity_id=str(product_model.id),
            action=AuditAction.UPDATE,
            actor=actor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=self._field_change_description(field_name, old_value, new_value),
        )

    async def record_product_model_archive(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="product_model",
            entity_id=str(product_model.id),
            action=AuditAction.ARCHIVE,
            actor=actor,
            field_name="status",
            old_value={"status": "active"},
            new_value={"status": "archived"},
            description=f"Product model '{product_model.model_name}' archived",
        )

    async def record_product_model_restore(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="product_model",
            entity_id=str(product_model.id),
            action=AuditAction.RESTORE,
            actor=actor,
            field_name="status",
            old_value={"status": "archived"},
            new_value={"status": "active"},
            description=f"Product model '{product_model.model_name}' restored",
        )

    async def record_inventory_create(
        self,
        item: InventoryItem,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.CREATE,
            actor=actor,
            inventory_item_id=item.id,
            new_value=await self._inventory_snapshot(item),
            description=f"Inventory item added (serial: {item.serial_number})",
        )

    async def record_inventory_location_change(
        self,
        item: InventoryItem,
        *,
        old_location_id: int,
        new_location_id: int,
        actor: AuditActor,
    ) -> None:
        old_name = await self._location_name(old_location_id)
        new_name = await self._location_name(new_location_id)
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.LOCATION_CHANGE,
            actor=actor,
            inventory_item_id=item.id,
            field_name="current_location",
            old_value={"current_location": old_name, "current_location_id": old_location_id},
            new_value={"current_location": new_name, "current_location_id": new_location_id},
            description=f"Location changed from {old_name} to {new_name}",
        )

    async def record_inventory_status_change(
        self,
        item: InventoryItem,
        *,
        old_status: InventoryStatus,
        new_status: InventoryStatus,
        actor: AuditActor,
        extra_new_value: dict[str, Any] | None = None,
    ) -> None:
        old_label = old_status.value.replace("_", " ").title()
        new_label = new_status.value.replace("_", " ").title()
        new_value: dict[str, Any] = {
            "status": new_status.value,
            "status_label": new_label,
        }
        if extra_new_value:
            new_value.update(extra_new_value)
        description = f"Status changed from {old_label} to {new_label}"
        if extra_new_value and extra_new_value.get("invoice_number"):
            description = (
                f"{description} (Invoice: {extra_new_value['invoice_number']})"
            )
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.STATUS_CHANGE,
            actor=actor,
            inventory_item_id=item.id,
            field_name="status",
            old_value={
                "status": old_status.value,
                "status_label": old_label,
            },
            new_value=new_value,
            description=description,
        )

    async def record_inventory_field_update(
        self,
        item: InventoryItem,
        *,
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.UPDATE,
            actor=actor,
            inventory_item_id=item.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=self._field_change_description(field_name, old_value, new_value),
        )

    async def record_system_action(
        self,
        *,
        entity_type: str,
        entity_id: str,
        description: str,
        actor: AuditActor | None = None,
        inventory_item_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
    ) -> None:
        """Record a system-initiated audit entry (e.g. future Tally sync)."""
        await self.record(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.SYSTEM_ACTION,
            actor=actor or AuditActor.system(display_name="System", role="system"),
            inventory_item_id=inventory_item_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description,
        )

    @staticmethod
    def _field_change_description(
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
    ) -> str:
        old_display = old_value.get(field_name, old_value)
        new_display = new_value.get(field_name, new_value)
        label = field_name.replace("_", " ").title()
        return f"{label} changed from {old_display} to {new_display}"

    async def _location_name(self, location_id: int) -> str:
        location = await self._session.get(Location, location_id)
        return location.name if location is not None else f"Location #{location_id}"

    async def _inventory_snapshot(self, item: InventoryItem) -> dict[str, Any]:
        location_name = await self._location_name(item.current_location_id)
        return {
            "serial_number": item.serial_number,
            "color": item.color,
            "status": item.status.value,
            "current_location": location_name,
            "current_location_id": item.current_location_id,
            "product_model_id": str(item.product_model_id),
        }

    async def _product_model_snapshot(self, product_model: ProductModel) -> dict[str, Any]:
        return {
            "brand_id": product_model.brand_id,
            "model_number": product_model.model_number,
            "model_name": product_model.model_name,
            "cpu": product_model.cpu,
            "gpu": product_model.gpu,
            "ram_gb": product_model.ram_gb,
            "storage_value": str(product_model.storage_value),
            "storage_unit": product_model.storage_unit.value,
            "storage_type": product_model.storage_type.value,
            "status": product_model.status.value,
        }
