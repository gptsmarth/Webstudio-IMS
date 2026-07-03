"""Notification business logic — centralized creation for Tally and system alerts."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationCreator,
    NotificationSeverity,
    NotificationType,
)
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam
from webstudio_backend.infrastructure.repositories.notification_filters import (
    NotificationSearchFilters,
)
from webstudio_backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


class NotificationService:
    """Single entry point for creating notifications across the system."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = NotificationRepository(session)

    async def list_notifications(
        self,
        filters: NotificationSearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[Notification]:
        return await self._repo.search(filters, page_params, sort_params)

    async def get_notification(self, notification_id: int) -> Notification | None:
        return await self._repo.get_by_id(notification_id)

    async def mark_read(self, notification_id: int) -> Notification:
        notification = await self._repo.require_by_id(notification_id)
        return await self._repo.mark_read(notification)

    async def mark_resolved(
        self, notification_id: int, *, resolved_by_user_id: int
    ) -> Notification:
        notification = await self._repo.require_by_id(notification_id)
        return await self._repo.mark_resolved(notification, resolved_by_user_id=resolved_by_user_id)

    async def create_notification(
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
        return await self._repo.create(
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            category=category,
            created_by=created_by,
            created_by_user_id=created_by_user_id,
            inventory_item_id=inventory_item_id,
            invoice_number=invoice_number,
            tally_company_name=tally_company_name,
            tally_voucher_number=tally_voucher_number,
            voucher_type=voucher_type,
            customer_name=customer_name,
            serial_number=serial_number,
            product_model_number=product_model_number,
        )

    async def create_duplicate_sale_notification(
        self,
        *,
        title: str,
        message: str,
        invoice_number: str,
        serial_number: str,
        tally_company_name: str | None = None,
        tally_voucher_number: str | None = None,
        voucher_type: str | None = None,
        customer_name: str | None = None,
        product_model_number: str | None = None,
        inventory_item_id: uuid.UUID | None = None,
    ) -> Notification:
        return await self.create_notification(
            notification_type=NotificationType.DUPLICATE_SALE,
            severity=NotificationSeverity.WARNING,
            title=title,
            message=message,
            invoice_number=invoice_number,
            serial_number=serial_number,
            tally_company_name=tally_company_name,
            tally_voucher_number=tally_voucher_number,
            voucher_type=voucher_type,
            customer_name=customer_name,
            product_model_number=product_model_number,
            inventory_item_id=inventory_item_id,
        )
