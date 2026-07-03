"""Sales workspace API tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import SaleSource
from webstudio_backend.infrastructure.database.models.sale import Sale


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
