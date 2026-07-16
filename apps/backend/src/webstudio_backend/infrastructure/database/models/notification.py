"""Notification ORM entity — operator-facing alerts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    NOTIFICATION_CATEGORY_ENUM_NAME,
    NOTIFICATION_CREATOR_ENUM_NAME,
    NOTIFICATION_SEVERITY_ENUM_NAME,
    NOTIFICATION_TYPE_ENUM_NAME,
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


def notification_status(notification: Notification) -> NotificationStatus:
    if notification.is_resolved:
        return NotificationStatus.RESOLVED
    if notification.is_read:
        return NotificationStatus.READ
    return NotificationStatus.UNREAD


class Notification(Base, PrimaryKeyMixin):
    __tablename__ = "notifications"

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name=NOTIFICATION_TYPE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(
            NotificationCategory,
            name=NOTIFICATION_CATEGORY_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(
            NotificationSeverity,
            name=NOTIFICATION_SEVERITY_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[NotificationCreator] = mapped_column(
        Enum(
            NotificationCreator,
            name=NOTIFICATION_CREATOR_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=NotificationCreator.SYSTEM,
        server_default="system",
    )
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{DATABASE_SCHEMA}.inventory_items.id",
            name="fk_notifications_inventory_item",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tally_company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tally_voucher_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voucher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_model_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
