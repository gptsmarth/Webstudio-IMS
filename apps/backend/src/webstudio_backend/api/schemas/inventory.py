"""Inventory API schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import InventoryStatus, StorageType, StorageUnit
from webstudio_backend.infrastructure.repositories.inventory_item_repository import InventoryItemDetailRow


class CreateInventoryItemRequest(BaseModel):
    serial_number: str
    product_model_id: uuid.UUID
    color: str
    current_location_id: int
    status: InventoryStatus = InventoryStatus.AVAILABLE
    purchase_date: date | None = None
    warranty_expiry: date | None = None


class UpdateInventoryItemRequest(BaseModel):
    serial_number: str | None = None
    product_model_id: uuid.UUID | None = None
    color: str | None = None
    current_location_id: int | None = None
    status: InventoryStatus | None = None
    purchase_date: date | None = None
    warranty_expiry: date | None = None


class InventoryItemDetail(BaseModel):
    id: uuid.UUID
    serial_number: str
    product_model_id: uuid.UUID
    brand_id: int
    brand_name: str
    model_number: str
    model_name: str
    cpu: str
    gpu: str | None
    ram_gb: int
    storage_value: Decimal
    storage_unit: StorageUnit
    storage_type: StorageType
    color: str
    current_location_id: int
    current_location_name: str
    status: InventoryStatus
    is_archived: bool
    purchase_date: date | None
    warranty_expiry: date | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: InventoryItemDetailRow) -> InventoryItemDetail:
        item = row.item
        pm = row.product_model
        return cls(
            id=item.id,
            serial_number=item.serial_number,
            product_model_id=item.product_model_id,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            model_number=pm.model_number,
            model_name=pm.model_name,
            cpu=pm.cpu,
            gpu=pm.gpu,
            ram_gb=pm.ram_gb,
            storage_value=pm.storage_value,
            storage_unit=pm.storage_unit,
            storage_type=pm.storage_type,
            color=item.color,
            current_location_id=item.current_location_id,
            current_location_name=row.location.name,
            status=item.status,
            is_archived=item.is_archived,
            purchase_date=item.purchase_date,
            warranty_expiry=item.warranty_expiry,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
