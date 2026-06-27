"""Report filter parameters and report type definitions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from webstudio_backend.infrastructure.database.enums import InventoryStatus, NotificationStatus


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
    brand_id: int | None = None
    location_id: int | None = None
    product_model_id: uuid.UUID | None = None
    user_id: int | None = None
    inventory_status: InventoryStatus | None = None
    notification_status: NotificationStatus | None = None
