"""Dashboard API and repository tests."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.dashboard_repository import DashboardRepository
from webstudio_backend.services.dashboard_service import DashboardService
from decimal import Decimal


async def _seed_inventory(db_session: AsyncSession) -> tuple[Brand, ProductModel, Location]:
    brand = await BrandRepository(db_session).create("ASUS")
    location = await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
    )
    store = await LocationRepository(db_session).create(
        "Store",
        location_type=LocationType.RETAIL_FLOOR,
    )
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="X1502ZA",
        model_name="Vivobook 15",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    repo = InventoryItemRepository(db_session)
    await repo.create(
        serial_number="SN-DASH-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await repo.create(
        serial_number="SN-DASH-002",
        product_model_id=product_model.id,
        color="Silver",
        current_location_id=store.id,
        status=InventoryStatus.SOLD,
    )
    sold_item = await repo.create(
        serial_number="SN-DASH-003",
        product_model_id=product_model.id,
        color="Blue",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    archived = await repo.create(
        serial_number="SN-DASH-004",
        product_model_id=product_model.id,
        color="Red",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await repo.archive(archived)
    del sold_item, store
    return brand, product_model, location


@pytest.mark.asyncio
async def test_operations_dashboard_snapshot(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_inventory(db_session)
    response = await api_client.get("/api/v1/dashboard", headers=main_admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_available_inventory"] == 2
    assert "as_of" in data
    assert "sales_summary" not in data
    assert "insights" not in data


@pytest.mark.asyncio
async def test_distribution_grouped_summaries(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_inventory(db_session)
    response = await api_client.get("/api/v1/dashboard/distribution", headers=main_admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_available_inventory"] == 2
    assert len(data["by_brand"]) == 1
    brand_row = data["by_brand"][0]
    assert brand_row["name"] == "ASUS"
    assert brand_row["available"] == 2
    assert brand_row["sold"] == 1
    assert brand_row["total"] == 3
    assert len(data["by_location"]) == 2
    assert len(data["by_product_model"]) == 1


@pytest.mark.asyncio
async def test_recent_activity_excludes_sync_and_includes_business_events(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_inventory(db_session)
    response = await api_client.get(
        "/api/v1/dashboard/recent-activity",
        headers=main_admin_headers,
        params={"limit": 20},
    )
    assert response.status_code == 200
    entries = response.json()["data"]
    assert len(entries) >= 1
    activity_types = {entry["activity_type"] for entry in entries}
    assert "inventory_created" in activity_types
    assert all(entry["entity_type"] not in {"sync_job", "tally_sync_log"} for entry in entries)


@pytest.mark.asyncio
@pytest.mark.parametrize("headers_fixture", ["main_admin_headers", "admin_headers"])
async def test_dashboard_rbac_admin_roles(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    headers_fixture: str,
) -> None:
    await _seed_inventory(db_session)
    headers_map = {
        "main_admin_headers": main_admin_headers,
        "admin_headers": admin_headers,
    }
    headers = headers_map[headers_fixture]
    for path in ("/api/v1/dashboard", "/api/v1/dashboard/distribution", "/api/v1/dashboard/recent-activity"):
        assert (await api_client.get(path, headers=headers)).status_code == 200


@pytest.mark.asyncio
async def test_salesperson_can_read_dashboard_endpoints(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_inventory(db_session)
    for path in ("/api/v1/dashboard", "/api/v1/dashboard/distribution", "/api/v1/dashboard/recent-activity"):
        assert (await api_client.get(path, headers=salesperson_headers)).status_code == 200


@pytest.mark.asyncio
async def test_dashboard_unauthenticated_rejected(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_dashboard_repository_uses_aggregate_queries(db_session: AsyncSession) -> None:
    repo = DashboardRepository(db_session)
    assert await repo.verify_aggregate_queries_use_sql() is True
    summary = await repo.get_inventory_summary()
    assert summary.total_inventory == 0


@pytest.mark.asyncio
async def test_dashboard_service_total_available(db_session: AsyncSession) -> None:
    await _seed_inventory(db_session)
    total = await DashboardService(db_session).get_total_available()
    assert total == 2


@pytest.mark.asyncio
async def test_distribution_excludes_archived_brands_and_locations(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand, product_model, warehouse = await _seed_inventory(db_session)
    brand_repo = BrandRepository(db_session)
    location_repo = LocationRepository(db_session)

    archived_brand = await brand_repo.create("AggBrand")
    archived_location = await location_repo.create(
        "AggLoc",
        location_type=LocationType.OTHER,
    )
    inventory_repo = InventoryItemRepository(db_session)
    await inventory_repo.create(
        serial_number="SN-AGG-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=archived_location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await inventory_repo.create(
        serial_number="SN-AGG-002",
        product_model_id=(
            await ProductModelRepository(db_session).create(
                brand_id=archived_brand.id,
                model_number="AGG-01",
                model_name="Agg Model",
                cpu="Intel i3",
                ram_gb=8,
                storage_value=Decimal("256"),
                storage_unit=StorageUnit.GB,
                storage_type=StorageType.SSD,
            )
        ).id,
        color="Silver",
        current_location_id=warehouse.id,
        status=InventoryStatus.AVAILABLE,
    )
    await brand_repo.update(archived_brand, is_active=False)
    await location_repo.update(archived_location, is_active=False)
    await db_session.commit()

    response = await api_client.get("/api/v1/dashboard/distribution", headers=main_admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    brand_names = {row["name"] for row in data["by_brand"]}
    location_names = {row["name"] for row in data["by_location"]}
    assert "AggBrand" not in brand_names
    assert "AggLoc" not in location_names
    assert "ASUS" in brand_names
    assert "Warehouse" in location_names

