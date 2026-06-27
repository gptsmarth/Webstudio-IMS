"""Notification repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.exceptions import (
    NotificationAlreadyResolvedError,
    NotificationNotFoundError,
    RequiredFieldError,
)
from webstudio_backend.infrastructure.repositories.notification_filters import NotificationSearchFilters
from webstudio_backend.infrastructure.repositories.notification_repository import NotificationRepository
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.services.setup_service import SetupService

TEST_PASSWORD = "SecurePass123!"


async def _ensure_main_admin(db_session: AsyncSession) -> int:
    await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username="mainadmin",
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    user = await UserRepository(db_session).get_by_username("mainadmin")
    assert user is not None
    return user.id


@pytest.mark.asyncio
async def test_create_notification(db_session: AsyncSession) -> None:
    repo = NotificationRepository(db_session)
    notification = await repo.create(
        notification_type=NotificationType.DUPLICATE_SALE,
        severity=NotificationSeverity.WARNING,
        title="Duplicate sale detected",
        message="Serial SN-001 already sold.",
        invoice_number="INV-100",
        serial_number="SN-001",
        tally_company_name="WEBSTUDIO",
    )
    assert notification.id is not None
    assert notification.category is NotificationCategory.TALLY_SYNC
    assert notification.is_read is False
    assert notification.is_resolved is False


@pytest.mark.asyncio
async def test_create_requires_title_and_message(db_session: AsyncSession) -> None:
    repo = NotificationRepository(db_session)
    with pytest.raises(RequiredFieldError):
        await repo.create(
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            severity=NotificationSeverity.INFO,
            title="   ",
            message="Valid message",
        )
    with pytest.raises(RequiredFieldError):
        await repo.create(
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            severity=NotificationSeverity.INFO,
            title="Valid title",
            message="   ",
        )


@pytest.mark.asyncio
async def test_search_filters_by_type_and_status(db_session: AsyncSession) -> None:
    repo = NotificationRepository(db_session)
    await repo.create(
        notification_type=NotificationType.DUPLICATE_SALE,
        severity=NotificationSeverity.WARNING,
        title="Duplicate",
        message="Duplicate sale",
    )
    inventory_alert = await repo.create(
        notification_type=NotificationType.INVENTORY_ALERT,
        severity=NotificationSeverity.INFO,
        title="Low stock",
        message="Warehouse low on model X",
        category=NotificationCategory.INVENTORY,
    )
    await repo.mark_read(inventory_alert)

    unread = await repo.search(
        NotificationSearchFilters(status=NotificationStatus.UNREAD),
        PageParams(page=1, page_size=10),
    )
    assert unread.total_items == 1

    read = await repo.search(
        NotificationSearchFilters(status=NotificationStatus.READ),
        PageParams(page=1, page_size=10),
    )
    assert read.total_items == 1
    assert read.items[0].id == inventory_alert.id

    by_type = await repo.search(
        NotificationSearchFilters(notification_type=NotificationType.INVENTORY_ALERT),
        PageParams(page=1, page_size=10),
    )
    assert by_type.total_items == 1


@pytest.mark.asyncio
async def test_mark_resolved_lifecycle(db_session: AsyncSession) -> None:
    user_id = await _ensure_main_admin(db_session)
    repo = NotificationRepository(db_session)
    notification = await repo.create(
        notification_type=NotificationType.SYNC_FAILURE,
        severity=NotificationSeverity.ERROR,
        title="Sync failed",
        message="Connection timeout",
    )
    resolved = await repo.mark_resolved(notification, resolved_by_user_id=user_id)
    assert resolved.is_read is True
    assert resolved.is_resolved is True
    assert resolved.resolved_at is not None
    assert resolved.resolved_by_user_id == user_id

    with pytest.raises(NotificationAlreadyResolvedError):
        await repo.mark_resolved(resolved, resolved_by_user_id=user_id)


@pytest.mark.asyncio
async def test_require_by_id_raises_when_missing(db_session: AsyncSession) -> None:
    repo = NotificationRepository(db_session)
    with pytest.raises(NotificationNotFoundError):
        await repo.require_by_id(999)
