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


class NotificationType(StrEnum):
    DUPLICATE_SALE = "duplicate_sale"
    SERIAL_NUMBER_MISSING = "serial_number_missing"
    PRODUCT_MODEL_MISSING = "product_model_missing"
    PRODUCT_MODEL_MISMATCH = "product_model_mismatch"
    TALLY_SYNC_COMPLETED = "tally_sync_completed"
    TALLY_SYNC_STARTED = "tally_sync_started"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    SYNC_FAILURE = "sync_failure"
    INVENTORY_ALERT = "inventory_alert"
    SYSTEM_NOTIFICATION = "system_notification"
    BACKUP_FAILED = "backup_failed"
    BACKUP_COMPLETED = "backup_completed"
    LOW_STORAGE = "low_storage"
    RECOVERY_COMPLETED = "recovery_completed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    BACKUP_VERIFICATION_FAILED = "backup_verification_failed"


class NotificationCategory(StrEnum):
    TALLY_SYNC = "tally_sync"
    INVENTORY = "inventory"
    SYSTEM = "system"


class NotificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class NotificationCreator(StrEnum):
    SYSTEM = "system"
    USER = "user"


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    RESOLVED = "resolved"


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


class TallyProcessingStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class TallySyncRunStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TallyLineStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TallyLineOutcome(StrEnum):
    SALE_APPLIED = "sale_applied"
    DUPLICATE_SALE = "duplicate_sale"
    SERIAL_NUMBER_MISSING = "serial_number_missing"
    PRODUCT_MODEL_MISSING = "product_model_missing"
    PRODUCT_MODEL_MISMATCH = "product_model_mismatch"
    IGNORED = "ignored"
    ERROR = "error"


HUMAN_USER_ROLES = frozenset({UserRole.MAIN_ADMIN, UserRole.ADMIN, UserRole.SALESPERSON})

LOCATION_TYPE_ENUM_NAME = "location_type"
PRODUCT_MODEL_STATUS_ENUM_NAME = "product_model_status"
STORAGE_UNIT_ENUM_NAME = "storage_unit"
STORAGE_TYPE_ENUM_NAME = "storage_type"
INVENTORY_STATUS_ENUM_NAME = "inventory_status"
SALE_SOURCE_ENUM_NAME = "sale_source"
NOTIFICATION_TYPE_ENUM_NAME = "notification_type"
NOTIFICATION_CATEGORY_ENUM_NAME = "notification_category"
NOTIFICATION_SEVERITY_ENUM_NAME = "notification_severity"
NOTIFICATION_CREATOR_ENUM_NAME = "notification_creator"
AUDIT_ACTION_ENUM_NAME = "audit_action"
AUDIT_SOURCE_ENUM_NAME = "audit_source"
USER_ROLE_ENUM_NAME = "user_role"
USER_STATUS_ENUM_NAME = "user_status"
THEME_PREFERENCE_ENUM_NAME = "theme_preference"
SETTING_VALUE_TYPE_ENUM_NAME = "setting_value_type"
TALLY_PROCESSING_STATUS_ENUM_NAME = "tally_processing_status"
TALLY_SYNC_RUN_STATUS_ENUM_NAME = "tally_sync_run_status"
TALLY_LINE_STATUS_ENUM_NAME = "tally_line_status"
TALLY_LINE_OUTCOME_ENUM_NAME = "tally_line_outcome"

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
    "NotificationCategory",
    "NotificationCreator",
    "NotificationSeverity",
    "NotificationStatus",
    "NotificationType",
    "NOTIFICATION_CATEGORY_ENUM_NAME",
    "NOTIFICATION_CREATOR_ENUM_NAME",
    "NOTIFICATION_SEVERITY_ENUM_NAME",
    "NOTIFICATION_TYPE_ENUM_NAME",
    "SaleSource",
    "TallyLineOutcome",
    "TallyLineStatus",
    "TallyProcessingStatus",
    "TallySyncRunStatus",
    "TALLY_LINE_OUTCOME_ENUM_NAME",
    "TALLY_LINE_STATUS_ENUM_NAME",
    "TALLY_PROCESSING_STATUS_ENUM_NAME",
    "TALLY_SYNC_RUN_STATUS_ENUM_NAME",
    "LocationType",
    "ProductModelStatus",
    "SettingValueType",
    "StorageType",
    "StorageUnit",
    "ThemePreference",
    "UserRole",
    "UserStatus",
]
