"""Inventory API schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    InventorySource,
    InventoryStatus,
    ProductCategory,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemDetailRow,
)


class CreateInventoryItemRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=128)
    product_model_id: uuid.UUID
    color: str = Field(min_length=1, max_length=64)
    current_location_id: int = Field(gt=0)
    status: InventoryStatus = InventoryStatus.AVAILABLE
    purchase_date: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)


class UpdateInventoryItemRequest(BaseModel):
    serial_number: str | None = Field(default=None, min_length=1, max_length=128)
    product_model_id: uuid.UUID | None = None
    color: str | None = Field(default=None, min_length=1, max_length=64)
    status: InventoryStatus | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)


class TransferLocationRequest(BaseModel):
    location_id: int = Field(gt=0, description="Destination location ID")


class MarkSoldRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=128)
    customer_name: str = Field(min_length=1, max_length=256)
    payment_mode: str = Field(min_length=1, max_length=64)
    sale_date: date
    sale_amount: Decimal | None = Field(default=None, ge=0)
    remarks: str | None = Field(default=None, max_length=2000)


class SaleDetail(BaseModel):
    id: int
    inventory_item_id: uuid.UUID
    serial_number: str
    sale_source: str
    sold_at: datetime
    invoice_number: str
    customer_name: str | None
    payment_mode: str | None
    sale_amount: float | None = None
    notes: str | None
    recorded_by_user_id: int | None
    created_at: datetime

    @classmethod
    def from_model(cls, sale, *, serial_number: str) -> SaleDetail:
        return cls(
            id=sale.id,
            inventory_item_id=sale.inventory_item_id,
            serial_number=serial_number,
            sale_source=sale.sale_source.value,
            sold_at=sale.sold_at,
            invoice_number=sale.invoice_number,
            customer_name=sale.customer_name,
            payment_mode=sale.payment_mode,
            sale_amount=float(sale.sale_amount) if sale.sale_amount is not None else None,
            notes=sale.notes,
            recorded_by_user_id=sale.recorded_by_user_id,
            created_at=sale.created_at,
        )


class InventoryItemDetail(BaseModel):
    id: uuid.UUID
    serial_number: str
    product_model_id: uuid.UUID
    brand_id: int
    brand_name: str
    category: ProductCategory = ProductCategory.LAPTOP
    accessory_kind: AccessoryKind | None = None
    part_number: str | None = None
    model_number: str
    model_name: str
    cpu: str | None = None
    gpu: str | None = None
    ram_gb: int | None = None
    storage_value: Decimal | None = None
    storage_unit: StorageUnit | None = None
    storage_type: StorageType | None = None
    color: str
    current_location_id: int
    current_location_name: str
    status: InventoryStatus
    is_archived: bool
    inventory_source: InventorySource = InventorySource.MANUAL
    purchase_date: date | None
    purchase_price: float | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(
        cls,
        row: InventoryItemDetailRow,
        *,
        include_purchase_price: bool = True,
    ) -> InventoryItemDetail:
        item = row.item
        pm = row.product_model
        return cls(
            id=item.id,
            serial_number=item.serial_number,
            product_model_id=item.product_model_id,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            category=pm.category,
            accessory_kind=pm.accessory_kind,
            part_number=pm.part_number,
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
            inventory_source=item.inventory_source,
            purchase_date=item.purchase_date,
            purchase_price=(
                float(item.purchase_price)
                if include_purchase_price and item.purchase_price is not None
                else None
            ),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class MarkSoldResponse(BaseModel):
    inventory: InventoryItemDetail
    sale: SaleDetail
