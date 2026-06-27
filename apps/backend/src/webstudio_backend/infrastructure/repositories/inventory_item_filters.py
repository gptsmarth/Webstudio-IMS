"""Inventory item search and filter parameters."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from webstudio_backend.infrastructure.database.enums import InventoryStatus


@dataclass(frozen=True, slots=True)
class InventorySearchFilters:
    brand_id: int | None = None
    product_model_id: UUID | None = None
    color: str | None = None
    current_location_id: int | None = None
    status: InventoryStatus | None = None
    search: str | None = None
