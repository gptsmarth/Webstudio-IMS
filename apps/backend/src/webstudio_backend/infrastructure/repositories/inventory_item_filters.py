"""Inventory item search and filter parameters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from webstudio_backend.infrastructure.database.enums import InventoryStatus


@dataclass(frozen=True, slots=True)
class InventorySearchFilters:
    brand_id: int | None = None
    product_model_id: UUID | None = None
    color: str | None = None
    current_location_id: int | None = None
    status: InventoryStatus | None = None
    is_archived: bool | None = None
    include_archived: bool = False
    serial_number: str | None = None
    brand_name: str | None = None
    product_model: str | None = None
    location_name: str | None = None
    search: str | None = None
    purchase_date_from: date | None = None
    purchase_date_to: date | None = None
    created_at_from: date | None = None
    created_at_to: date | None = None
