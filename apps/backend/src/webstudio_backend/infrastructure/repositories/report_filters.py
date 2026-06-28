"""Report filter parameters and report type definitions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from webstudio_backend.infrastructure.database.enums import (
    AuditAction,
    AuditSource,
    InventoryStatus,
    LocationType,
    NotificationCategory,
    NotificationStatus,
    NotificationType,
    SaleSource,
)


class ReportType(StrEnum):
    INVENTORY = "inventory"
    SALES = "sales"
    LOCATION = "location"
    BRAND = "brand"
    PRODUCT_MODEL = "product_model"
    AUDIT = "audit"
    NOTIFICATION = "notification"


class ExportFormat(StrEnum):
    XLSX = "xlsx"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class ReportFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    purchase_date_from: date | None = None
    purchase_date_to: date | None = None
    brand_id: int | None = None
    location_id: int | None = None
    location_type: LocationType | None = None
    product_model_id: uuid.UUID | None = None
    user_id: int | None = None
    inventory_status: InventoryStatus | None = None
    is_archived: bool | None = None
    serial_number: str | None = None
    color: str | None = None
    notification_status: NotificationStatus | None = None
    notification_type: NotificationType | None = None
    notification_category: NotificationCategory | None = None
    invoice_number: str | None = None
    customer_name: str | None = None
    payment_mode: str | None = None
    sale_source: SaleSource | None = None
    audit_action: AuditAction | None = None
    audit_source: AuditSource | None = None
    actor_role: str | None = None
    search: str | None = None
    sort_field: str | None = None
    sort_direction: str | None = None
