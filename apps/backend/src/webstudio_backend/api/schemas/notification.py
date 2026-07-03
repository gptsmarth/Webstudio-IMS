"""Notification API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from webstudio_backend.infrastructure.database.models.notification import (
    Notification,
    notification_status,
)


class NotificationDetail(BaseModel):
    id: int
    notification_type: NotificationType
    title: str
    description: str
    category: NotificationCategory
    severity: NotificationSeverity
    status: NotificationStatus
    created_by: NotificationCreator
    created_by_user_id: int | None = None
    inventory_item_id: uuid.UUID | None = None
    invoice_number: str | None = None
    tally_company_name: str | None = None
    tally_voucher_number: str | None = None
    voucher_type: str | None = None
    customer_name: str | None = None
    serial_number: str | None = None
    product_model_number: str | None = None
    is_read: bool
    is_resolved: bool
    resolved_at: datetime | None = None
    resolved_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> NotificationDetail:
        return cls(
            id=notification.id,
            notification_type=notification.notification_type,
            title=notification.title,
            description=notification.message,
            category=notification.category,
            severity=notification.severity,
            status=notification_status(notification),
            created_by=notification.created_by,
            created_by_user_id=notification.created_by_user_id,
            inventory_item_id=notification.inventory_item_id,
            invoice_number=notification.invoice_number,
            tally_company_name=notification.tally_company_name,
            tally_voucher_number=notification.tally_voucher_number,
            voucher_type=notification.voucher_type,
            customer_name=notification.customer_name,
            serial_number=notification.serial_number,
            product_model_number=notification.product_model_number,
            is_read=notification.is_read,
            is_resolved=notification.is_resolved,
            resolved_at=notification.resolved_at,
            resolved_by_user_id=notification.resolved_by_user_id,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )


class NotificationSearchQuery(BaseModel):
    notification_type: NotificationType | None = None
    category: NotificationCategory | None = None
    severity: NotificationSeverity | None = None
    status: NotificationStatus | None = None
    is_read: bool | None = None
    is_resolved: bool | None = None
    tally_company_name: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
