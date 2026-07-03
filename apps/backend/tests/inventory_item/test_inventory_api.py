"""Inventory API integration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository


def _create_payload(product_model: ProductModel, location: Location, serial: str) -> dict:
    return {
        "serial_number": serial,
        "product_model_id": str(product_model.id),
        "color": "Black",
        "current_location_id": location.id,
        "status": "available",
        "purchase_date": "2026-01-15",
    }


@pytest.mark.asyncio
async def test_create_and_get_inventory(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    create = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-API-001"),
    )
    assert create.status_code == 201
    body = create.json()["data"]
    assert body["serial_number"] == "SN-API-001"
    assert body["brand_name"] == "ASUS"
    assert body["purchase_date"] == "2026-01-15"

    get_resp = await api_client.get(
        f"/api/v1/inventory/{body['id']}",
        headers=main_admin_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["serial_number"] == "SN-API-001"


@pytest.mark.asyncio
async def test_duplicate_serial_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    payload = _create_payload(product_model, location, "SN-DUP-001")
    assert (
        await api_client.post("/api/v1/inventory", headers=main_admin_headers, json=payload)
    ).status_code == 201
    duplicate = await api_client.post("/api/v1/inventory", headers=main_admin_headers, json=payload)
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_get_by_serial_case_insensitive(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-LOOKUP-001"),
    )
    response = await api_client.get(
        "/api/v1/inventory/by-serial/sn-lookup-001",
        headers=main_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["serial_number"] == "SN-LOOKUP-001"


@pytest.mark.asyncio
async def test_serial_search_returns_at_most_one(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-UNIQUE-999"),
    )
    listed = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={"serial_number": "SN-UNIQUE-999"},
    )
    assert listed.status_code == 200
    assert listed.json()["meta"]["total_records"] == 1
    assert len(listed.json()["data"]) == 1


@pytest.mark.asyncio
async def test_update_inventory(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    created = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-UPD-001"),
    )
    item_id = created.json()["data"]["id"]
    updated = await api_client.patch(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
        json={"color": "Silver", "status": "reserved"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["color"] == "Silver"
    assert updated.json()["data"]["status"] == "reserved"


@pytest.mark.asyncio
async def test_archive_and_restore(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    created = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-ARCH-001"),
    )
    item_id = created.json()["data"]["id"]
    archived = await api_client.post(
        f"/api/v1/inventory/{item_id}/archive",
        headers=main_admin_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["is_archived"] is True

    hidden = await api_client.get("/api/v1/inventory", headers=main_admin_headers)
    assert hidden.json()["meta"]["total_records"] == 0

    visible = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={"include_archived": "true"},
    )
    assert visible.json()["meta"]["total_records"] == 1

    restored = await api_client.post(
        f"/api/v1/inventory/{item_id}/restore",
        headers=main_admin_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["is_archived"] is False


@pytest.mark.asyncio
async def test_list_filters_and_pagination(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    from webstudio_backend.infrastructure.database.enums import LocationType
    from webstudio_backend.infrastructure.repositories import LocationRepository

    store = await LocationRepository(db_session).create(
        "Store Floor",
        location_type=LocationType.RETAIL_FLOOR,
    )
    for index, serial in enumerate(("SN-F1", "SN-F2", "SN-F3")):
        await api_client.post(
            "/api/v1/inventory",
            headers=main_admin_headers,
            json={
                **_create_payload(product_model, location if index < 2 else store, serial),
                "purchase_date": f"2026-0{index + 1}-01",
            },
        )

    filtered = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={
            "brand_id": brand.id,
            "status": "available",
            "current_location_id": location.id,
            "page": 1,
            "page_size": 1,
            "sort": "serial_number:asc",
        },
    )
    assert filtered.status_code == 200
    meta = filtered.json()["meta"]
    assert meta["total_records"] == 2
    assert meta["total_pages"] == 2
    assert meta["current_page"] == 1
    assert len(filtered.json()["data"]) == 1

    by_brand_name = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={"brand": "asus"},
    )
    assert by_brand_name.json()["meta"]["total_records"] == 3


@pytest.mark.asyncio
async def test_salesperson_can_read_not_write(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    created = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-RBAC-001"),
    )
    item_id = created.json()["data"]["id"]

    read_ok = await api_client.get(f"/api/v1/inventory/{item_id}", headers=salesperson_headers)
    assert read_ok.status_code == 200

    write_forbidden = await api_client.post(
        "/api/v1/inventory",
        headers=salesperson_headers,
        json=_create_payload(product_model, location, "SN-RBAC-002"),
    )
    assert write_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_rejected(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/inventory")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mutations_create_audit_entries(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    created = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_create_payload(product_model, location, "SN-AUDIT-001"),
    )
    item_id = created.json()["data"]["id"]

    await api_client.patch(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
        json={"color": "Blue"},
    )
    await api_client.post(
        f"/api/v1/inventory/{item_id}/archive",
        headers=main_admin_headers,
    )

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(inventory_item_id=item_id),
        PageParams(page=1, page_size=20),
    )
    actions = {entry.action.value for entry in audits.items}
    assert "CREATE" in actions
    assert "UPDATE" in actions
    assert "ARCHIVE" in actions


@pytest.mark.asyncio
async def test_invalid_product_model_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    location: Location,
) -> None:
    import uuid

    response = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json={
            "serial_number": "SN-BAD-001",
            "product_model_id": str(uuid.uuid4()),
            "color": "Black",
            "current_location_id": location.id,
            "status": "available",
        },
    )
    assert response.status_code == 422
