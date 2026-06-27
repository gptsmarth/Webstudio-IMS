"""Notification search filter parameters."""

from __future__ import annotations

from dataclasses import dataclass

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)


@dataclass(frozen=True, slots=True)
class NotificationSearchFilters:
    notification_type: NotificationType | None = None
    category: NotificationCategory | None = None
    severity: NotificationSeverity | None = None
    status: NotificationStatus | None = None
    is_read: bool | None = None
    is_resolved: bool | None = None
    tally_company_name: str | None = None
