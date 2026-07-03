"""Inventory operations API tests — Sprint 2B."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import LocationType
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories import LocationRepository
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository


def _create_payload(product_model: ProductModel, location: Location, serial: str) -> dict:
    return {
        "serial_number": serial,
        "product_model_id": str(product_model.id),
        "color": "Black",
        "current_location_id": location.id,
        "status": "available",
    }


def _sale_payload(**overrides) -> dict:
    payload = {
        "invoice_number": "INV-1001",
        "customer_name": "Acme Corp",
        "payment_mode": "UPI",
        "sale_date": "2026-06-15",
        "remarks": "Counter sale",
    }
    payload.update(overrides)
    return payload


async def _create_item(
    api_client: AsyncClient,
    headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    serial: str,
) -> str:
    response = await api_client.post(
        "/api/v1/inventory",
        headers=headers,
        json=_create_payload(product_model, location, serial),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_mark_sold_success(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-001"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(),
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["inventory"]["status"] == "sold"
    assert body["sale"]["invoice_number"] == "INV-1001"
    assert body["sale"]["customer_name"] == "Acme Corp"
    assert body["sale"]["payment_mode"] == "UPI"
    assert body["sale"]["sale_source"] == "manual"


@pytest.mark.asyncio
async def test_mark_sold_requires_available_status(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-002"
    )
    await api_client.patch(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
        json={"status": "reserved"},
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-1002"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mark_sold_already_sold_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-003"
    )
    first = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-1003"),
    )
    assert first.status_code == 200

    second = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-1004"),
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_mark_sold_archived_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-004"
    )
    await api_client.post(f"/api/v1/inventory/{item_id}/archive", headers=main_admin_headers)

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-1005"),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_mark_sold_salesperson_forbidden(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-005"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=salesperson_headers,
        json=_sale_payload(invoice_number="INV-1006"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mark_sold_admin_allowed(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-006"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=admin_headers,
        json=_sale_payload(invoice_number="INV-1007"),
    )
    assert response.status_code == 200
    assert response.json()["data"]["inventory"]["status"] == "sold"


@pytest.mark.asyncio
async def test_mark_sold_creates_audit_entries(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-SOLD-007"
    )
    await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-1008"),
    )

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(inventory_item_id=item_id),
        PageParams(page=1, page_size=50),
    )
    actions = {entry.action.value for entry in audits.items}
    assert "CREATE" in actions
    assert "STATUS_CHANGE" in actions


@pytest.mark.asyncio
async def test_location_transfer_success(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    store = await LocationRepository(db_session).create(
        "Store Floor",
        location_type=LocationType.RETAIL_FLOOR,
    )
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-001"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": store.id},
    )
    assert response.status_code == 200
    assert response.json()["data"]["current_location_id"] == store.id
    assert response.json()["data"]["current_location_name"] == "Store Floor"


@pytest.mark.asyncio
async def test_location_transfer_archived_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    store = await LocationRepository(db_session).create(
        "Back Room",
        location_type=LocationType.WAREHOUSE,
    )
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-002"
    )
    await api_client.post(f"/api/v1/inventory/{item_id}/archive", headers=main_admin_headers)

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": store.id},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_location_transfer_sold_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    store = await LocationRepository(db_session).create(
        "Showroom",
        location_type=LocationType.RETAIL_FLOOR,
    )
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-003"
    )
    await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-2001"),
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": store.id},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SOLD_ITEM_CANNOT_MOVE"


@pytest.mark.asyncio
async def test_location_transfer_invalid_location(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-004"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": 999999},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_location_transfer_same_location_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-005"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": location.id},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_location_transfer_salesperson_allowed(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    store = await LocationRepository(db_session).create(
        "Sales Floor",
        location_type=LocationType.RETAIL_FLOOR,
    )
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-006"
    )

    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=salesperson_headers,
        json={"location_id": store.id},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_location_transfer_creates_audit_entry(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    store = await LocationRepository(db_session).create(
        "Dispatch",
        location_type=LocationType.WAREHOUSE,
    )
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-MOVE-007"
    )
    await api_client.patch(
        f"/api/v1/inventory/{item_id}/location",
        headers=main_admin_headers,
        json={"location_id": store.id},
    )

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(inventory_item_id=item_id),
        PageParams(page=1, page_size=50),
    )
    actions = {entry.action.value for entry in audits.items}
    assert "LOCATION_CHANGE" in actions
