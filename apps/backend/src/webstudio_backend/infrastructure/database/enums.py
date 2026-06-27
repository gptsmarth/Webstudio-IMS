"""PostgreSQL-aligned enum types for ORM models."""

from __future__ import annotations

from enum import StrEnum


class LocationType(StrEnum):
    RETAIL_FLOOR = "retail_floor"
    WAREHOUSE = "warehouse"
    OTHER = "other"


class ProductModelStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class StorageUnit(StrEnum):
    GB = "GB"
    TB = "TB"


class StorageType(StrEnum):
    SSD = "SSD"
    HDD = "HDD"


class InventoryStatus(StrEnum):
    RECEIVED = "received"
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"


LOCATION_TYPE_ENUM_NAME = "location_type"
PRODUCT_MODEL_STATUS_ENUM_NAME = "product_model_status"
STORAGE_UNIT_ENUM_NAME = "storage_unit"
STORAGE_TYPE_ENUM_NAME = "storage_type"
INVENTORY_STATUS_ENUM_NAME = "inventory_status"

__all__ = [
    "INVENTORY_STATUS_ENUM_NAME",
    "LOCATION_TYPE_ENUM_NAME",
    "PRODUCT_MODEL_STATUS_ENUM_NAME",
    "STORAGE_TYPE_ENUM_NAME",
    "STORAGE_UNIT_ENUM_NAME",
    "InventoryStatus",
    "LocationType",
    "ProductModelStatus",
    "StorageType",
    "StorageUnit",
]
