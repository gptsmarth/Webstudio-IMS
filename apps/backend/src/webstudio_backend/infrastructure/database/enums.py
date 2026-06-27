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


class SaleSource(StrEnum):
    TALLY = "tally"
    MANUAL = "manual"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    ARCHIVE = "ARCHIVE"
    RESTORE = "RESTORE"
    STATUS_CHANGE = "STATUS_CHANGE"
    LOCATION_CHANGE = "LOCATION_CHANGE"
    SYSTEM_ACTION = "SYSTEM_ACTION"


class AuditSource(StrEnum):
    MANUAL = "MANUAL"
    TALLY_SYNC = "TALLY_SYNC"
    BACKGROUND_JOB = "BACKGROUND_JOB"
    SYSTEM = "SYSTEM"


class UserRole(StrEnum):
    MAIN_ADMIN = "main_admin"
    ADMIN = "admin"
    SALESPERSON = "salesperson"
    SERVICE_ACCOUNT = "service_account"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ThemePreference(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class SettingValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"
    CRON = "cron"


HUMAN_USER_ROLES = frozenset({UserRole.MAIN_ADMIN, UserRole.ADMIN, UserRole.SALESPERSON})

LOCATION_TYPE_ENUM_NAME = "location_type"
PRODUCT_MODEL_STATUS_ENUM_NAME = "product_model_status"
STORAGE_UNIT_ENUM_NAME = "storage_unit"
STORAGE_TYPE_ENUM_NAME = "storage_type"
INVENTORY_STATUS_ENUM_NAME = "inventory_status"
SALE_SOURCE_ENUM_NAME = "sale_source"
AUDIT_ACTION_ENUM_NAME = "audit_action"
AUDIT_SOURCE_ENUM_NAME = "audit_source"
USER_ROLE_ENUM_NAME = "user_role"
USER_STATUS_ENUM_NAME = "user_status"
THEME_PREFERENCE_ENUM_NAME = "theme_preference"
SETTING_VALUE_TYPE_ENUM_NAME = "setting_value_type"

__all__ = [
    "AUDIT_ACTION_ENUM_NAME",
    "AUDIT_SOURCE_ENUM_NAME",
    "AuditAction",
    "AuditSource",
    "HUMAN_USER_ROLES",
    "INVENTORY_STATUS_ENUM_NAME",
    "LOCATION_TYPE_ENUM_NAME",
    "PRODUCT_MODEL_STATUS_ENUM_NAME",
    "SETTING_VALUE_TYPE_ENUM_NAME",
    "STORAGE_TYPE_ENUM_NAME",
    "STORAGE_UNIT_ENUM_NAME",
    "THEME_PREFERENCE_ENUM_NAME",
    "USER_ROLE_ENUM_NAME",
    "USER_STATUS_ENUM_NAME",
    "SALE_SOURCE_ENUM_NAME",
    "InventoryStatus",
    "SaleSource",
    "LocationType",
    "ProductModelStatus",
    "SettingValueType",
    "StorageType",
    "StorageUnit",
    "ThemePreference",
    "UserRole",
    "UserStatus",
]
