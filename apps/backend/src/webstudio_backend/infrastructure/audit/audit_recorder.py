"""Automatic audit log recording for repository mutations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_snapshots import entity_ref
from webstudio_backend.infrastructure.database.enums import (
    AuditAction,
    AuditSource,
    InventoryStatus,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.models.user import User
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
        source: AuditSource | None = None,
    ) -> None:
        resolved_source = source or (
            AuditSource.MANUAL if actor.user_id is not None else AuditSource.SYSTEM
        )
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
            source=resolved_source,
        )

    async def record_brand_create(self, brand: Brand, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="brand",
            entity_id=str(brand.id),
            action=AuditAction.CREATE,
            actor=actor,
            new_value={
                "brand": entity_ref(entity_id=brand.id, name=brand.name),
                "is_active": brand.is_active,
            },
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
                "location": entity_ref(entity_id=location.id, name=location.name),
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
        old_ref = await self._location_ref(old_location_id)
        new_ref = await self._location_ref(new_location_id)
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.LOCATION_CHANGE,
            actor=actor,
            inventory_item_id=item.id,
            field_name="current_location",
            old_value={"current_location": old_ref},
            new_value={"current_location": new_ref},
            description=(
                f"Location changed from {old_ref['name']} to {new_ref['name']}"
            ),
        )

    async def record_inventory_status_change(
        self,
        item: InventoryItem,
        *,
        old_status: InventoryStatus,
        new_status: InventoryStatus,
        actor: AuditActor,
        extra_new_value: dict[str, Any] | None = None,
        source: AuditSource | None = None,
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
            source=source,
        )

    async def record_inventory_product_model_change(
        self,
        item: InventoryItem,
        *,
        old_product_model_id: uuid.UUID,
        new_product_model_id: uuid.UUID,
        actor: AuditActor,
    ) -> None:
        old_ref = await self._product_model_ref(old_product_model_id)
        new_ref = await self._product_model_ref(new_product_model_id)
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.UPDATE,
            actor=actor,
            inventory_item_id=item.id,
            field_name="product_model",
            old_value={"product_model": old_ref},
            new_value={"product_model": new_ref},
            description=(
                f"Product model changed from {old_ref['name']} to {new_ref['name']}"
            ),
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

    async def record_inventory_archive(
        self,
        item: InventoryItem,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.ARCHIVE,
            actor=actor,
            inventory_item_id=item.id,
            old_value={"is_archived": False},
            new_value={"is_archived": True},
            description=f"Inventory item archived (serial: {item.serial_number})",
        )

    async def record_inventory_restore(
        self,
        item: InventoryItem,
        *,
        actor: AuditActor,
    ) -> None:
        await self.record(
            entity_type="inventory_item",
            entity_id=str(item.id),
            action=AuditAction.RESTORE,
            actor=actor,
            inventory_item_id=item.id,
            old_value={"is_archived": True},
            new_value={"is_archived": False},
            description=f"Inventory item restored (serial: {item.serial_number})",
        )

    async def record_sale_create(
        self,
        sale: Sale,
        *,
        actor: AuditActor,
        source: AuditSource | None = None,
    ) -> None:
        await self.record(
            entity_type="sale",
            entity_id=str(sale.id),
            action=AuditAction.CREATE,
            actor=actor,
            inventory_item_id=sale.inventory_item_id,
            new_value={
                "sale_id": sale.id,
                "sale_source": sale.sale_source.value,
                "invoice_number": sale.invoice_number,
                "printed_invoice_number": sale.printed_invoice_number or sale.invoice_number,
                "tally_voucher_number": sale.tally_voucher_number,
                "customer_name": sale.customer_name,
                "payment_mode": sale.payment_mode,
                "sold_at": sale.sold_at.isoformat(),
                "notes": sale.notes,
            },
            description=f"Sale recorded (Invoice: {sale.printed_invoice_number or sale.invoice_number})",
            source=source,
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
        source: AuditSource = AuditSource.SYSTEM,
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
            source=source,
        )

    async def record_user_create(self, user: User, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.CREATE,
            actor=actor,
            new_value=self._user_snapshot(user),
            description=f"User '{user.username}' created",
        )

    async def record_user_update(
        self,
        user: User,
        *,
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        actor: AuditActor,
        description: str | None = None,
    ) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.UPDATE,
            actor=actor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description or self._field_change_description(field_name, old_value, new_value),
        )

    async def record_user_disable(self, user: User, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.ARCHIVE,
            actor=actor,
            field_name="status",
            old_value={"status": "active"},
            new_value={"status": "disabled"},
            description=f"User '{user.username}' deactivated",
        )

    async def record_user_enable(self, user: User, *, actor: AuditActor) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.RESTORE,
            actor=actor,
            field_name="status",
            old_value={"status": "disabled"},
            new_value={"status": "active"},
            description=f"User '{user.username}' activated",
        )

    async def record_system_initialize(
        self,
        *,
        company_name: str,
        main_admin_username: str,
        user_id: int,
    ) -> None:
        await self.record(
            entity_type="system",
            entity_id="initialization",
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor(user_id=user_id, display_name=main_admin_username, role="main_admin"),
            new_value={"company_name": company_name, "username": main_admin_username},
            description=f"System initialized for {company_name}",
            source=AuditSource.SYSTEM,
        )

    async def record_auth_login_success(self, user: User) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor(user_id=user.id, display_name=user.display_name or user.username, role=user.role.value),
            description=f"User '{user.username}' logged in",
            source=AuditSource.MANUAL,
        )

    async def record_auth_login_failure(self, username: str) -> None:
        await self.record(
            entity_type="user",
            entity_id=username,
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor.system(display_name="Unknown", role="system"),
            new_value={"username": username},
            description=f"Failed login attempt for '{username}'",
            source=AuditSource.SYSTEM,
        )

    async def record_auth_logout(self, user: User) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor(user_id=user.id, display_name=user.display_name or user.username, role=user.role.value),
            description=f"User '{user.username}' logged out",
            source=AuditSource.MANUAL,
        )

    async def record_recovery_key_generated(self, user: User, *, reason: str) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor(user_id=user.id, display_name=user.display_name or user.username, role=user.role.value),
            new_value={"reason": reason},
            description="Main Admin recovery key generated",
            source=AuditSource.SYSTEM,
        )

    async def record_recovery_key_used(self, user: User) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor.system(display_name="Recovery", role="system"),
            description=f"Main Admin recovery key used for '{user.username}'",
            source=AuditSource.SYSTEM,
        )

    async def record_main_admin_password_recovered(self, user: User) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.UPDATE,
            actor=AuditActor.system(display_name="Recovery", role="system"),
            field_name="password",
            old_value={"password_recovered": False},
            new_value={"password_recovered": True},
            description=f"Main Admin password recovered for '{user.username}'",
            source=AuditSource.SYSTEM,
        )

    async def record_recovery_key_regenerated(self, user: User) -> None:
        await self.record(
            entity_type="user",
            entity_id=str(user.id),
            action=AuditAction.SYSTEM_ACTION,
            actor=AuditActor.system(display_name="Recovery", role="system"),
            description=f"Main Admin recovery key regenerated for '{user.username}'",
            source=AuditSource.SYSTEM,
        )

    @staticmethod
    def _user_snapshot(user: User) -> dict[str, Any]:
        return {
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
            "status": user.status.value,
        }

    @staticmethod
    def _field_change_description(
        field_name: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
    ) -> str:
        old_display = AuditRecorder._display_value(old_value.get(field_name, old_value))
        new_display = AuditRecorder._display_value(new_value.get(field_name, new_value))
        label = field_name.replace("_", " ").title()
        return f"{label} changed from {old_display} to {new_display}"

    @staticmethod
    def _display_value(value: object) -> object:
        if isinstance(value, dict) and "name" in value:
            return value["name"]
        return value

    async def _location_ref(self, location_id: int) -> dict[str, Any]:
        location = await self._session.get(Location, location_id)
        name = location.name if location is not None else f"Location #{location_id}"
        return entity_ref(entity_id=location_id, name=name)

    async def _brand_ref(self, brand_id: int) -> dict[str, Any]:
        brand = await self._session.get(Brand, brand_id)
        name = brand.name if brand is not None else f"Brand #{brand_id}"
        return entity_ref(entity_id=brand_id, name=name)

    async def _product_model_ref(self, product_model_id: uuid.UUID) -> dict[str, Any]:
        product_model = await self._session.get(ProductModel, product_model_id)
        if product_model is None:
            return entity_ref(entity_id=product_model_id, name=f"Model {product_model_id}")
        return {
            "id": str(product_model.id),
            "name": product_model.model_name,
            "model_number": product_model.model_number,
        }

    async def _inventory_snapshot(self, item: InventoryItem) -> dict[str, Any]:
        return {
            "serial_number": item.serial_number,
            "color": item.color,
            "status": item.status.value,
            "current_location": await self._location_ref(item.current_location_id),
            "product_model": await self._product_model_ref(item.product_model_id),
        }

    async def _product_model_snapshot(self, product_model: ProductModel) -> dict[str, Any]:
        return {
            "brand": await self._brand_ref(product_model.brand_id),
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
