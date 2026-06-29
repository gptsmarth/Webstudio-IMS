"""Emit in-app notifications for backup and disaster recovery events."""

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

LOW_STORAGE_BYTES = 512 * 1024 * 1024


class BackupAlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._settings = SystemSettingRepository(session)
        self._notifications = NotificationService(session)

    async def is_enabled(self) -> bool:
        notifications_on = await self._settings.get_bool("notifications_enabled", default=True)
        backup_alerts = await self._settings.get_bool("backup_alerts_enabled", default=True)
        system_alerts = await self._settings.get_bool("system_alerts_enabled", default=True)
        return notifications_on and backup_alerts and system_alerts

    async def notify_backup_completed(
        self,
        *,
        filename: str,
        verification_status: str,
        size_bytes: int,
    ) -> None:
        if not await self.is_enabled():
            return
        severity = (
            NotificationSeverity.WARNING
            if verification_status in {"warning", "failed"}
            else NotificationSeverity.INFO
        )
        await self._notifications.create_notification(
            notification_type=NotificationType.BACKUP_COMPLETED,
            severity=severity,
            title="Backup completed",
            message=(
                f"Backup '{filename}' completed with status '{verification_status}' "
                f"({size_bytes} bytes)."
            ),
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_backup_failed(self, *, filename: str, detail: str) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.BACKUP_FAILED,
            severity=NotificationSeverity.ERROR,
            title="Backup failed",
            message=f"Backup '{filename}' failed: {detail}",
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_scheduled_backup_failed(self, *, detail: str) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.BACKUP_FAILED,
            severity=NotificationSeverity.ERROR,
            title="Scheduled backup failed",
            message=detail,
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def maybe_notify_low_storage(self, *, storage_free_bytes: int) -> None:
        if storage_free_bytes >= LOW_STORAGE_BYTES:
            return
        if not await self.is_enabled():
            return
        free_mb = max(storage_free_bytes // (1024 * 1024), 0)
        await self._notifications.create_notification(
            notification_type=NotificationType.LOW_STORAGE,
            severity=NotificationSeverity.WARNING,
            title="Low backup storage",
            message=(
                f"Only {free_mb} MB free on the backup volume. "
                "Create space or change backup folder."
            ),
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_recovery_completed(
        self,
        *,
        filename: str,
        restore_scope: str,
        verification_status: str,
    ) -> None:
        if not await self.is_enabled():
            return
        severity = (
            NotificationSeverity.WARNING
            if verification_status in {"warning", "failed"}
            else NotificationSeverity.INFO
        )
        await self._notifications.create_notification(
            notification_type=NotificationType.RESTORE_COMPLETED,
            severity=severity,
            title="Restore completed",
            message=(
                f"Restore of '{filename}' ({restore_scope}) finished with status "
                f"'{verification_status}'."
            ),
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_restore_started(self, *, filename: str, restore_scope: str) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.RESTORE_STARTED,
            severity=NotificationSeverity.INFO,
            title="Restore started",
            message=f"Restore of '{filename}' ({restore_scope}) has started.",
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_restore_failed(
        self,
        *,
        filename: str,
        restore_scope: str,
        detail: str,
    ) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.RESTORE_FAILED,
            severity=NotificationSeverity.ERROR,
            title="Restore failed",
            message=f"Restore of '{filename}' ({restore_scope}) failed: {detail}",
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )

    async def notify_backup_verification_failed(self, *, filename: str, detail: str) -> None:
        if not await self.is_enabled():
            return
        await self._notifications.create_notification(
            notification_type=NotificationType.BACKUP_VERIFICATION_FAILED,
            severity=NotificationSeverity.ERROR,
            title="Backup verification failed",
            message=f"Backup '{filename}' failed verification: {detail}",
            category=NotificationCategory.SYSTEM,
            created_by=NotificationCreator.SYSTEM,
        )
