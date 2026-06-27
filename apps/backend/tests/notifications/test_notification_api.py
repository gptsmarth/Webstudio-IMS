"""Notification Center API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationSeverity,
    NotificationType,
)
from webstudio_backend.services.notification_service import NotificationService


async def _seed_notifications(db_session: AsyncSession) -> list[int]:
    service = NotificationService(db_session)
    ids: list[int] = []
    duplicate = await service.create_duplicate_sale_notification(
        title="Duplicate sale",
        message="Serial already sold",
        invoice_number="INV-001",
        serial_number="SN-DUP-001",
        tally_company_name="WEBSTUDIO",
    )
    ids.append(duplicate.id)
    inventory = await service.create_notification(
        notification_type=NotificationType.INVENTORY_ALERT,
        severity=NotificationSeverity.WARNING,
        title="Inventory alert",
        message="Item nearing warranty expiry",
        category=NotificationCategory.INVENTORY,
    )
    ids.append(inventory.id)
    system = await service.create_notification(
        notification_type=NotificationType.SYSTEM_NOTIFICATION,
        severity=NotificationSeverity.INFO,
        title="Maintenance",
        message="Scheduled maintenance tonight",
        category=NotificationCategory.SYSTEM,
    )
    ids.append(system.id)
    await db_session.commit()
    return ids


@pytest.mark.asyncio
async def test_list_notifications_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/notifications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_and_get_notification(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    ids = await _seed_notifications(db_session)
    list_response = await api_client.get("/api/v1/notifications", headers=main_admin_headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["meta"]["total_items"] == 3
    assert len(payload["data"]) == 3

    detail_response = await api_client.get(
        f"/api/v1/notifications/{ids[0]}",
        headers=main_admin_headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["notification_type"] == "duplicate_sale"
    assert detail["description"] == "Serial already sold"
    assert detail["status"] == "unread"
    assert detail["category"] == "tally_sync"


@pytest.mark.asyncio
async def test_get_notification_not_found(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    response = await api_client.get("/api/v1/notifications/9999", headers=main_admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_mark_read_lifecycle(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    notification_id = (await _seed_notifications(db_session))[0]
    read_response = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=main_admin_headers,
    )
    assert read_response.status_code == 200
    data = read_response.json()["data"]
    assert data["is_read"] is True
    assert data["status"] == "read"
    assert data["is_resolved"] is False

    second_read = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=main_admin_headers,
    )
    assert second_read.status_code == 200
    assert second_read.json()["data"]["status"] == "read"


@pytest.mark.asyncio
async def test_resolve_notification_lifecycle(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    notification_id = (await _seed_notifications(db_session))[1]
    resolve_response = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/resolve",
        headers=main_admin_headers,
    )
    assert resolve_response.status_code == 200
    data = resolve_response.json()["data"]
    assert data["is_resolved"] is True
    assert data["is_read"] is True
    assert data["status"] == "resolved"
    assert data["resolved_by_user_id"] is not None

    duplicate_resolve = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/resolve",
        headers=main_admin_headers,
    )
    assert duplicate_resolve.status_code == 409
    assert duplicate_resolve.json()["error"]["code"] == "NOTIFICATION_ALREADY_RESOLVED"


@pytest.mark.asyncio
async def test_salesperson_can_read_but_not_resolve(
    api_client: AsyncClient,
    db_session: AsyncSession,
    salesperson_headers: dict[str, str],
) -> None:
    notification_id = (await _seed_notifications(db_session))[0]
    list_response = await api_client.get("/api/v1/notifications", headers=salesperson_headers)
    assert list_response.status_code == 200

    read_response = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=salesperson_headers,
    )
    assert read_response.status_code == 200

    resolve_response = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/resolve",
        headers=salesperson_headers,
    )
    assert resolve_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_resolve(
    api_client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    notification_id = (await _seed_notifications(db_session))[0]
    response = await api_client.patch(
        f"/api/v1/notifications/{notification_id}/resolve",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "resolved"


@pytest.mark.asyncio
async def test_filter_by_notification_type(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    await _seed_notifications(db_session)
    response = await api_client.get(
        "/api/v1/notifications",
        params={"notification_type": "inventory_alert"},
        headers=main_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total_items"] == 1
    assert response.json()["data"][0]["notification_type"] == "inventory_alert"


@pytest.mark.asyncio
async def test_filter_by_is_read_and_is_resolved(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    ids = await _seed_notifications(db_session)
    await api_client.patch(
        f"/api/v1/notifications/{ids[0]}/read",
        headers=main_admin_headers,
    )
    await api_client.patch(
        f"/api/v1/notifications/{ids[1]}/resolve",
        headers=main_admin_headers,
    )

    unread = await api_client.get(
        "/api/v1/notifications",
        params={"is_read": "false", "is_resolved": "false"},
        headers=main_admin_headers,
    )
    assert unread.json()["meta"]["total_items"] == 1

    resolved = await api_client.get(
        "/api/v1/notifications",
        params={"is_resolved": "true"},
        headers=main_admin_headers,
    )
    assert resolved.json()["meta"]["total_items"] == 1
    assert resolved.json()["data"][0]["status"] == "resolved"


@pytest.mark.asyncio
async def test_filter_by_status(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
) -> None:
    ids = await _seed_notifications(db_session)
    await api_client.patch(
        f"/api/v1/notifications/{ids[0]}/read",
        headers=main_admin_headers,
    )
    response = await api_client.get(
        "/api/v1/notifications",
        params={"status": "read"},
        headers=main_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total_items"] == 1
    assert response.json()["data"][0]["status"] == "read"


@pytest.mark.asyncio
async def test_notification_service_create_for_tally_reuse(db_session: AsyncSession) -> None:
    service = NotificationService(db_session)
    notification = await service.create_duplicate_sale_notification(
        title="Duplicate",
        message="Already sold",
        invoice_number="INV-200",
        serial_number="SN-200",
    )
    assert notification.notification_type is NotificationType.DUPLICATE_SALE
    assert notification.category.value == "tally_sync"
