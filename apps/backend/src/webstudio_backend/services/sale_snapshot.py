"""Denormalized product snapshot stored on sales for immutable history."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemDetailRow,
)


@dataclass(frozen=True, slots=True)
class SaleProductSnapshot:
    serial_number: str
    product_model_id: uuid.UUID
    brand_id: int
    brand_name: str
    model_number: str
    model_name: str
    color: str
    cpu: str | None
    gpu: str | None
    ram_gb: int | None
    storage_value: Decimal | None
    storage_unit: str | None
    storage_type: str | None
    location_name: str
    purchase_price: Decimal | None = None

    @classmethod
    def from_detail(cls, detail: InventoryItemDetailRow) -> SaleProductSnapshot:
        item = detail.item
        model = detail.product_model
        return cls(
            serial_number=item.serial_number,
            product_model_id=model.id,
            brand_id=detail.brand.id,
            brand_name=detail.brand.name,
            model_number=model.model_number,
            model_name=model.model_name,
            color=item.color,
            cpu=model.cpu,
            gpu=model.gpu,
            ram_gb=model.ram_gb,
            storage_value=model.storage_value,
            storage_unit=(
                model.storage_unit.value
                if model.storage_unit is not None and hasattr(model.storage_unit, "value")
                else (str(model.storage_unit) if model.storage_unit is not None else None)
            ),
            storage_type=(
                model.storage_type.value
                if model.storage_type is not None and hasattr(model.storage_type, "value")
                else (str(model.storage_type) if model.storage_type is not None else None)
            ),
            location_name=detail.location.name,
            purchase_price=item.purchase_price,
        )

    def apply_to(self, sale: Sale) -> None:
        sale.snapshot_serial_number = self.serial_number
        sale.snapshot_product_model_id = self.product_model_id
        sale.snapshot_brand_id = self.brand_id
        sale.snapshot_brand_name = self.brand_name
        sale.snapshot_model_number = self.model_number
        sale.snapshot_model_name = self.model_name
        sale.snapshot_color = self.color
        sale.snapshot_cpu = self.cpu
        sale.snapshot_gpu = self.gpu
        sale.snapshot_ram_gb = self.ram_gb
        sale.snapshot_storage_value = self.storage_value
        sale.snapshot_storage_unit = self.storage_unit
        sale.snapshot_storage_type = self.storage_type
        sale.snapshot_location_name = self.location_name
        sale.snapshot_purchase_price = self.purchase_price
