"""Sprint 2C inventory API hardening tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories import LocationRepository
from webstudio_backend.infrastructure.database.enums import LocationType


def _payload(product_model: ProductModel, location: Location, serial: str) -> dict:
    return {
        "serial_number": serial,
        "product_model_id": str(product_model.id),
        "color": "Black",
        "current_location_id": location.id,
        "status": "available",
    }


async def _create(
    client: AsyncClient,
    headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    serial: str,
) -> str:
    response = await client.post(
        "/api/v1/inventory",
        headers=headers,
        json=_payload(product_model, location, serial),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _assert_error_envelope(response, *, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == code
    assert "message" in body["error"]
    assert "request_id" in body
    assert "correlation_id" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_duplicate_serial_returns_standard_error_envelope(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    payload = _payload(product_model, location, "SN-ERR-001")
    assert (await api_client.post("/api/v1/inventory", headers=main_admin_headers, json=payload)).status_code == 201
    duplicate = await api_client.post("/api/v1/inventory", headers=main_admin_headers, json=payload)
    _assert_error_envelope(duplicate, status=409, code="SERIAL_NUMBER_DUPLICATE")


@pytest.mark.asyncio
async def test_serial_not_found_error_code(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    response = await api_client.get(
        "/api/v1/inventory/by-serial/does-not-exist",
        headers=main_admin_headers,
    )
    _assert_error_envelope(response, status=404, code="SERIAL_NOT_FOUND")


@pytest.mark.asyncio
async def test_empty_patch_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create(api_client, main_admin_headers, product_model, location, "SN-ERR-002")
    response = await api_client.patch(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
        json={},
    )
    _assert_error_envelope(response, status=422, code="VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_invalid_sort_field_standard_error(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    response = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={"sort": "invalid_field:asc"},
    )
    _assert_error_envelope(response, status=422, code="VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_success_response_includes_request_metadata(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    response = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=_payload(product_model, location, "SN-META-001"),
    )
    assert response.status_code == 201
    body = response.json()
    assert "data" in body
    assert "request_id" in body
    assert "correlation_id" in body
    assert "timestamp" in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body", "allowed_headers"),
    [
        ("GET", "/api/v1/inventory", None, ("main_admin", "admin", "salesperson")),
        ("POST", "/api/v1/inventory", {"needs_item": True}, ("main_admin", "admin")),
        ("PATCH", "/api/v1/inventory/{id}", {"color": "Silver"}, ("main_admin", "admin")),
        ("POST", "/api/v1/inventory/{id}/archive", None, ("main_admin", "admin")),
        ("POST", "/api/v1/inventory/{id}/restore", None, ("main_admin", "admin")),
        ("PATCH", "/api/v1/inventory/{id}/location", {"location_id": 0}, ("main_admin", "admin")),
        ("PATCH", "/api/v1/inventory/{id}/mark-sold", {"needs_sale": True}, ("main_admin", "admin")),
    ],
)
async def test_rbac_matrix(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
    method: str,
    path: str,
    json_body: dict | None,
    allowed_headers: tuple[str, ...],
) -> None:
    store = await LocationRepository(db_session).create(
        "RBAC Store",
        location_type=LocationType.RETAIL_FLOOR,
    )
    item_id = await _create(api_client, main_admin_headers, product_model, location, f"SN-RBAC-{uuid.uuid4().hex[:8]}")

    headers_by_role = {
        "main_admin": main_admin_headers,
        "admin": admin_headers,
        "salesperson": salesperson_headers,
    }

    resolved_path = path.replace("{id}", item_id)
    body = dict(json_body or {})
    if body.pop("needs_item", None):
        body = _payload(product_model, location, f"SN-RBAC-NEW-{uuid.uuid4().hex[:8]}")
    if body.pop("needs_sale", None):
        body = {
            "invoice_number": "INV-RBAC",
            "customer_name": "Customer",
            "payment_mode": "Cash",
            "sale_date": "2026-06-01",
        }
    if "location_id" in body and body["location_id"] == 0:
        body["location_id"] = store.id

    for role, headers in headers_by_role.items():
        if method == "GET":
            response = await api_client.get(resolved_path, headers=headers)
        elif method == "POST":
            response = await api_client.post(resolved_path, headers=headers, json=body or None)
        else:
            response = await api_client.patch(resolved_path, headers=headers, json=body or None)

        if role in allowed_headers:
            assert response.status_code != 403, f"{role} should have access to {method} {path}"
        else:
            assert response.status_code == 403
            _assert_error_envelope(response, status=403, code="PERMISSION_DENIED")


@pytest.mark.asyncio
async def test_serial_list_filter_returns_at_most_one(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    serial = "SN-PERF-LIST-001"
    await _create(api_client, main_admin_headers, product_model, location, serial)
    response = await api_client.get(
        "/api/v1/inventory",
        headers=main_admin_headers,
        params={"serial_number": serial},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total_records"] == 1
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_performance_indexes_exist(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'webstudio'
              AND tablename = 'inventory_items'
            """,
        ),
    )
    index_names = {row[0] for row in result.all()}
    assert "ix_inventory_items_serial_number_lower" in index_names
    assert "ix_inventory_items_list_default" in index_names
    assert "ix_inventory_items_location_status" in index_names
    assert "ix_inventory_items_model_status" in index_names


@pytest.mark.asyncio
async def test_serial_lookup_uses_indexed_query(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    serial = "SN-PERF-LOOKUP-001"
    await _create(api_client, main_admin_headers, product_model, location, serial)

    plan = await db_session.execute(
        text(
            """
            EXPLAIN
            SELECT ii.id
            FROM webstudio.inventory_items ii
            WHERE lower(ii.serial_number) = lower(:serial)
            LIMIT 1
            """,
        ),
        {"serial": serial},
    )
    plan_text = "\n".join(row[0] for row in plan.all())
    assert "Index Scan" in plan_text or "Bitmap Index Scan" in plan_text

    response = await api_client.get(
        f"/api/v1/inventory/by-serial/{serial.lower()}",
        headers=main_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["serial_number"] == serial
