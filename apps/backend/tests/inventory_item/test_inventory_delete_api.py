"""Serial (inventory item) hard-delete API regression tests.

The desktop Stock page calls ``DELETE /api/v1/inventory/{id}`` to remove a
wrong serial completely. These tests pin the endpoint contract so a failing
delete surfaces as a backend test failure, not a client-side "network error".
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel

from .conftest import sample_inventory_payload


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
        json=sample_inventory_payload(
            product_model_id=str(product_model.id),
            current_location_id=location.id,
            serial_number=serial,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_delete_serial_removes_item_completely(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-DEL-001"
    )

    response = await api_client.delete(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert response.status_code == 204, response.text

    lookup = await api_client.get(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert lookup.status_code == 404

    # Serial is fully released — the same serial can be registered again.
    recreated = await api_client.post(
        "/api/v1/inventory",
        headers=main_admin_headers,
        json=sample_inventory_payload(
            product_model_id=str(product_model.id),
            current_location_id=location.id,
            serial_number="SN-DEL-001",
        ),
    )
    assert recreated.status_code == 201, recreated.text


@pytest.mark.asyncio
async def test_delete_archived_serial_allowed(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    """Archived (but unsold) serials must also be fully deletable."""
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-DEL-ARC"
    )
    archived = await api_client.post(
        f"/api/v1/inventory/{item_id}/archive",
        headers=main_admin_headers,
    )
    assert archived.status_code == 200, archived.text

    response = await api_client.delete(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert response.status_code == 204, response.text

    lookup = await api_client.get(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert lookup.status_code == 404


@pytest.mark.asyncio
async def test_delete_serial_with_audit_history(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
    db_session: AsyncSession,
) -> None:
    """Items touched by edits/transfers accumulate audit rows — delete must still work."""
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-DEL-AUD"
    )
    updated = await api_client.patch(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
        json={"color": "Silver"},
    )
    assert updated.status_code == 200, updated.text

    response = await api_client.delete(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert response.status_code == 204, response.text

    # Audit rows survive with the FK cleared (history preserved, serial gone).
    remaining = await db_session.execute(
        text("SELECT COUNT(*) FROM webstudio.audit_logs WHERE inventory_item_id IS NOT NULL"),
    )
    assert remaining.scalar_one() == 0


@pytest.mark.asyncio
async def test_delete_sold_serial_blocked(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model: ProductModel,
    location: Location,
) -> None:
    item_id = await _create_item(
        api_client, main_admin_headers, product_model, location, "SN-DEL-SOLD"
    )
    sold = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json={
            "invoice_number": "INV-DEL-1",
            "customer_name": "Walk-in",
            "payment_mode": "cash",
            "sale_date": "2026-07-01",
        },
    )
    assert sold.status_code == 200, sold.text

    response = await api_client.delete(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert response.status_code in {409, 422}, response.text
