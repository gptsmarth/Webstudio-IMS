"""PostgreSQL-aligned enum types for ORM models."""

from __future__ import annotations

from enum import StrEnum


class LocationType(StrEnum):
    RETAIL_FLOOR = "retail_floor"
    WAREHOUSE = "warehouse"
    OTHER = "other"


LOCATION_TYPE_ENUM_NAME = "location_type"

__all__ = ["LOCATION_TYPE_ENUM_NAME", "LocationType"]
