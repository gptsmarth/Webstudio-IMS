"""Emit in-app notifications for critical security events when audit alerts are enabled."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationType,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.notification_service import NotificationService


class SecurityAlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._notifications = NotificationService(session)

    async def is_enabled(self) -> bool:
        return await self._settings.get_bool("audit_alerts_enabled", default=False)

    async def emit(
        self,
        *,
        title: str,
        message: str,
        severity: NotificationSeverity,
    ) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            severity=severity,
            title=title,
            message=message,
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )
