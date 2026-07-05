"""Sales workspace API tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    SaleSource,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    LocationRepository,
    ProductModelRepository,
)


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
    product_model_id: uuid.UUID,
    location_id: int,
    serial: str,
) -> str:
    response = await api_client.post(
        "/api/v1/inventory",
        headers=headers,
        json={
            "serial_number": serial,
            "product_model_id": str(product_model_id),
            "color": "Black",
            "current_location_id": location_id,
            "status": "available",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession):
    return await BrandRepository(db_session).create("ASUS")


@pytest_asyncio.fixture
async def location(db_session: AsyncSession):
    return await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
    )


@pytest_asyncio.fixture
async def product_model(db_session: AsyncSession, brand):
    return await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="X1502ZA-EJ541WS",
        model_name="Vivobook 15",
        cpu="Intel Core i5-1235U",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )


@pytest.mark.asyncio
async def test_list_sales_allows_null_inventory_item_id(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    sale = Sale(
        inventory_item_id=None,
        sale_source=SaleSource.MANUAL,
        sold_at=datetime.now(UTC),
        invoice_number="INV-SNAPSHOT-001",
        snapshot_serial_number="SN-OLD-001",
        snapshot_brand_name="HP",
        snapshot_model_number="840-G8",
        snapshot_model_name="EliteBook 840",
        snapshot_location_name="Warehouse",
    )
    db_session.add(sale)
    await db_session.commit()

    response = await api_client.get("/api/v1/sales", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    match = next((row for row in payload if row["invoice_number"] == "INV-SNAPSHOT-001"), None)
    assert match is not None
    assert match["inventory_item_id"] is None
    assert match["serial_number"] == "SN-OLD-001"
    assert match["brand_name"] == "HP"


@pytest.mark.asyncio
async def test_get_sale_detail_with_snapshot_only(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    sale = Sale(
        inventory_item_id=None,
        sale_source=SaleSource.MANUAL,
        sold_at=datetime.now(UTC),
        invoice_number="INV-SNAPSHOT-002",
        snapshot_serial_number="SN-OLD-002",
        snapshot_brand_id=7,
        snapshot_brand_name="Lenovo",
        snapshot_product_model_id=uuid.uuid4(),
        snapshot_model_number="T14",
        snapshot_model_name="ThinkPad T14",
        snapshot_location_name="Retail floor",
        snapshot_cpu="Intel i7",
        snapshot_ram_gb=16,
    )
    db_session.add(sale)
    await db_session.commit()
    await db_session.refresh(sale)

    response = await api_client.get(f"/api/v1/sales/{sale.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["inventory_item_id"] is None
    assert data["serial_number"] == "SN-OLD-002"
    assert data["brand_name"] == "Lenovo"


@pytest.mark.asyncio
async def test_cancel_sale_restores_inventory_to_available(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    product_model,
    location,
) -> None:
    item_id = await _create_item(
        api_client,
        main_admin_headers,
        product_model.id,
        location.id,
        "SN-CANCEL-001",
    )
    sold = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-CANCEL-001"),
    )
    assert sold.status_code == 200
    sale_id = sold.json()["data"]["sale"]["id"]

    response = await api_client.post(
        f"/api/v1/sales/{sale_id}/cancel",
        headers=main_admin_headers,
        json={"reason": "Customer return"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["inventory"]["id"] == item_id
    assert body["inventory"]["status"] == InventoryStatus.AVAILABLE.value
    assert body["inventory"]["serial_number"] == "SN-CANCEL-001"
    assert body["sale"]["invoice_number"] == "INV-CANCEL-001"
    assert body["sale"]["serial_number"] == "SN-CANCEL-001"
    assert body["sale"]["cancellation_reason"] == "Customer return"

    list_response = await api_client.get("/api/v1/sales", headers=main_admin_headers)
    assert list_response.status_code == 200
    invoices = [row["invoice_number"] for row in list_response.json()["data"]]
    assert "INV-CANCEL-001" not in invoices

    detail_response = await api_client.get(
        f"/api/v1/sales/{sale_id}",
        headers=main_admin_headers,
    )
    assert detail_response.status_code == 404

    inventory_response = await api_client.get(
        f"/api/v1/inventory/{item_id}",
        headers=main_admin_headers,
    )
    assert inventory_response.status_code == 200
    assert inventory_response.json()["data"]["status"] == InventoryStatus.AVAILABLE.value


@pytest.mark.asyncio
async def test_cancel_sale_salesperson_forbidden(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    product_model,
    location,
) -> None:
    item_id = await _create_item(
        api_client,
        main_admin_headers,
        product_model.id,
        location.id,
        "SN-CANCEL-002",
    )
    sold = await api_client.patch(
        f"/api/v1/inventory/{item_id}/mark-sold",
        headers=main_admin_headers,
        json=_sale_payload(invoice_number="INV-CANCEL-002"),
    )
    sale_id = sold.json()["data"]["sale"]["id"]

    response = await api_client.post(
        f"/api/v1/sales/{sale_id}/cancel",
        headers=salesperson_headers,
        json={},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cancel_sale_without_linked_inventory_rejected(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    sale = Sale(
        inventory_item_id=None,
        sale_source=SaleSource.MANUAL,
        sold_at=datetime.now(UTC),
        invoice_number="INV-SNAPSHOT-ONLY",
        snapshot_serial_number="SN-OLD-003",
    )
    db_session.add(sale)
    await db_session.commit()
    await db_session.refresh(sale)

    response = await api_client.post(
        f"/api/v1/sales/{sale.id}/cancel",
        headers=admin_headers,
        json={},
    )
    assert response.status_code == 422
