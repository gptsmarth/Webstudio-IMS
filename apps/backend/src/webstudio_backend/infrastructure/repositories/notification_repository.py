"""Notification persistence repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam, apply_sorting
from webstudio_backend.infrastructure.repositories.exceptions import (
    NotificationAlreadyResolvedError,
    NotificationNotFoundError,
    RequiredFieldError,
)
from webstudio_backend.infrastructure.repositories.notification_filters import (
    NotificationSearchFilters,
)

_CATEGORY_BY_TYPE: dict[NotificationType, NotificationCategory] = {
    NotificationType.DUPLICATE_SALE: NotificationCategory.TALLY_SYNC,
    NotificationType.SERIAL_NUMBER_MISSING: NotificationCategory.TALLY_SYNC,
    NotificationType.PRODUCT_MODEL_MISSING: NotificationCategory.TALLY_SYNC,
    NotificationType.TALLY_SYNC_COMPLETED: NotificationCategory.TALLY_SYNC,
    NotificationType.SYNC_FAILURE: NotificationCategory.TALLY_SYNC,
    NotificationType.INVENTORY_ALERT: NotificationCategory.INVENTORY,
    NotificationType.SYSTEM_NOTIFICATION: NotificationCategory.SYSTEM,
    NotificationType.BACKUP_FAILED: NotificationCategory.SYSTEM,
    NotificationType.BACKUP_COMPLETED: NotificationCategory.SYSTEM,
    NotificationType.LOW_STORAGE: NotificationCategory.SYSTEM,
    NotificationType.RECOVERY_COMPLETED: NotificationCategory.SYSTEM,
    NotificationType.RESTORE_STARTED: NotificationCategory.SYSTEM,
    NotificationType.RESTORE_COMPLETED: NotificationCategory.SYSTEM,
    NotificationType.RESTORE_FAILED: NotificationCategory.SYSTEM,
    NotificationType.BACKUP_VERIFICATION_FAILED: NotificationCategory.SYSTEM,
}


class NotificationRepository(SqlAlchemyRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def get_by_id(self, entity_id: int) -> Notification | None:
        return await self._session.get(self._model, entity_id)

    async def require_by_id(self, notification_id: int) -> Notification:
        notification = await self.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(notification_id)
        return notification

    async def create(
        self,
        *,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        category: NotificationCategory | None = None,
        created_by: NotificationCreator = NotificationCreator.SYSTEM,
        created_by_user_id: int | None = None,
        inventory_item_id: uuid.UUID | None = None,
        invoice_number: str | None = None,
        tally_company_name: str | None = None,
        tally_voucher_number: str | None = None,
        voucher_type: str | None = None,
        customer_name: str | None = None,
        serial_number: str | None = None,
        product_model_number: str | None = None,
    ) -> Notification:
        normalized_title = title.strip()
        normalized_message = message.strip()
        if not normalized_title:
            raise RequiredFieldError("title")
        if not normalized_message:
            raise RequiredFieldError("message")

        resolved_category = category or _CATEGORY_BY_TYPE[notification_type]
        return await self.add(
            Notification(
                notification_type=notification_type,
                category=resolved_category,
                severity=severity,
                title=normalized_title,
                message=normalized_message,
                created_by=created_by,
                created_by_user_id=created_by_user_id,
                inventory_item_id=inventory_item_id,
                invoice_number=invoice_number.strip() if invoice_number else None,
                tally_company_name=tally_company_name.strip() if tally_company_name else None,
                tally_voucher_number=tally_voucher_number.strip() if tally_voucher_number else None,
                voucher_type=voucher_type.strip() if voucher_type else None,
                customer_name=customer_name.strip() if customer_name else None,
                serial_number=serial_number.strip() if serial_number else None,
                product_model_number=product_model_number.strip() if product_model_number else None,
            ),
        )

    async def search(
        self,
        filters: NotificationSearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[Notification]:
        statement = select(Notification)
        statement = self._apply_filters(statement, filters)
        if sort_params:
            column_map = {column.key: column for column in Notification.__table__.columns}
            statement = apply_sorting(statement, sort_params, column_map)
        else:
            statement = statement.order_by(Notification.created_at.desc())
        return await paginate(self._session, statement, page_params)

    async def mark_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.updated_at = datetime.now(UTC)
            await self._session.flush()
            await self._session.refresh(notification)
        return notification

    async def mark_resolved(
        self,
        notification: Notification,
        *,
        resolved_by_user_id: int,
    ) -> Notification:
        if notification.is_resolved:
            raise NotificationAlreadyResolvedError(notification.id)
        now = datetime.now(UTC)
        notification.is_read = True
        notification.is_resolved = True
        notification.resolved_at = now
        notification.resolved_by_user_id = resolved_by_user_id
        notification.updated_at = now
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    def _apply_filters(
        self,
        statement,
        filters: NotificationSearchFilters,
    ):
        if filters.notification_type is not None:
            statement = statement.where(Notification.notification_type == filters.notification_type)
        if filters.category is not None:
            statement = statement.where(Notification.category == filters.category)
        if filters.severity is not None:
            statement = statement.where(Notification.severity == filters.severity)
        if filters.is_read is not None:
            statement = statement.where(Notification.is_read.is_(filters.is_read))
        if filters.is_resolved is not None:
            statement = statement.where(Notification.is_resolved.is_(filters.is_resolved))
        if filters.status is not None:
            if filters.status is NotificationStatus.UNREAD:
                statement = statement.where(
                    Notification.is_read.is_(False),
                    Notification.is_resolved.is_(False),
                )
            elif filters.status is NotificationStatus.READ:
                statement = statement.where(
                    Notification.is_read.is_(True),
                    Notification.is_resolved.is_(False),
                )
            elif filters.status is NotificationStatus.RESOLVED:
                statement = statement.where(Notification.is_resolved.is_(True))
        if filters.tally_company_name is not None:
            term = filters.tally_company_name.strip()
            if term:
                statement = statement.where(Notification.tally_company_name.ilike(f"%{term}%"))
        return statement
