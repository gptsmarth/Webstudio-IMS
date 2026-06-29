"""Reference data (Brands and Locations) API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location


@pytest.mark.asyncio
async def test_brands_rbac_and_crud(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
) -> None:
    # 1. Read access
    # Unauthorized
    resp = await api_client.get("/api/v1/brands")
    assert resp.status_code == 401

    # Salesperson can read (empty list)
    resp = await api_client.get("/api/v1/brands", headers=salesperson_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []

    # 2. Write access (Salesperson forbidden, Admin allowed)
    payload = {
        "name": "Apple",
        "short_name": "APL",
        "logo_filename": "apple.svg",
        "display_order": 1,
        "is_active": True,
    }
    resp = await api_client.post("/api/v1/brands", json=payload, headers=salesperson_headers)
    assert resp.status_code == 403

    resp = await api_client.post("/api/v1/brands", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    brand_data = resp.json()["data"]
    assert brand_data["name"] == "Apple"
    assert brand_data["short_name"] == "APL"
    assert brand_data["display_order"] == 1
    brand_id = brand_data["id"]

    # 3. Prevent Duplicate Name (case-insensitive)
    dup_payload = {
        "name": "  aPpLe  ",
        "short_name": "APL2",
    }
    resp = await api_client.post("/api/v1/brands", json=dup_payload, headers=admin_headers)
    assert resp.status_code == 409

    # 4. GET Detail
    resp = await api_client.get(f"/api/v1/brands/{brand_id}", headers=salesperson_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Apple"

    # GET detail not found
    resp = await api_client.get("/api/v1/brands/99999", headers=salesperson_headers)
    assert resp.status_code == 404

    # 5. PATCH Brand
    update_payload = {
        "name": "Apple Inc.",
        "short_name": "AAPL",
        "display_order": 2,
    }
    resp = await api_client.patch(f"/api/v1/brands/{brand_id}", json=update_payload, headers=admin_headers)
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["name"] == "Apple Inc."
    assert updated["short_name"] == "AAPL"
    assert updated["display_order"] == 2

    # PATCH conflict name
    # Create another brand
    await api_client.post("/api/v1/brands", json={"name": "Dell"}, headers=admin_headers)
    resp = await api_client.patch(f"/api/v1/brands/{brand_id}", json={"name": "Dell"}, headers=admin_headers)
    assert resp.status_code == 409

    # 6. Archive / Restore
    # Archive
    resp = await api_client.post(f"/api/v1/brands/{brand_id}/archive", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False

    # Restore
    resp = await api_client.post(f"/api/v1/brands/{brand_id}/restore", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_locations_rbac_and_crud(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
) -> None:
    # 1. Read access
    # Unauthorized
    resp = await api_client.get("/api/v1/locations")
    assert resp.status_code == 401

    # Salesperson can read
    resp = await api_client.get("/api/v1/locations", headers=salesperson_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []

    # 2. Write access
    payload = {
        "name": "Yamunanagar Outlet",
        "location_type": "retail_floor",
        "sort_order": 1,
        "is_active": True,
    }
    resp = await api_client.post("/api/v1/locations", json=payload, headers=salesperson_headers)
    assert resp.status_code == 403

    resp = await api_client.post("/api/v1/locations", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    loc_data = resp.json()["data"]
    assert loc_data["name"] == "Yamunanagar Outlet"
    assert loc_data["location_type"] == "retail_floor"
    loc_id = loc_data["id"]

    # 3. Prevent duplicate location name
    resp = await api_client.post("/api/v1/locations", json={"name": "Yamunanagar Outlet", "location_type": "warehouse"}, headers=admin_headers)
    assert resp.status_code == 409

    # 4. GET Detail
    resp = await api_client.get(f"/api/v1/locations/{loc_id}", headers=salesperson_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Yamunanagar Outlet"

    # GET detail not found
    resp = await api_client.get("/api/v1/locations/99999", headers=salesperson_headers)
    assert resp.status_code == 404

    # 5. PATCH Location
    update_payload = {
        "name": "Yamunanagar Store",
        "location_type": "retail_floor",
        "sort_order": 5,
    }
    resp = await api_client.patch(f"/api/v1/locations/{loc_id}", json=update_payload, headers=admin_headers)
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["name"] == "Yamunanagar Store"
    assert updated["sort_order"] == 5

    # 6. Archive / Restore
    # Archive
    resp = await api_client.post(f"/api/v1/locations/{loc_id}/archive", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False

    # Restore
    resp = await api_client.post(f"/api/v1/locations/{loc_id}/restore", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_location_archive_preview_and_transfer(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from decimal import Decimal

    from webstudio_backend.infrastructure.database.enums import (
        InventoryStatus,
        LocationType,
        StorageType,
        StorageUnit,
    )
    from webstudio_backend.infrastructure.repositories import (
        BrandRepository,
        InventoryItemRepository,
        LocationRepository,
        ProductModelRepository,
    )

    brand = await BrandRepository(db_session).create("Transfer Brand")
    source = await LocationRepository(db_session).create("Source Loc", location_type=LocationType.WAREHOUSE)
    destination = await LocationRepository(db_session).create("Dest Loc", location_type=LocationType.RETAIL_FLOOR)
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="TR-01",
        model_name="Transfer Model",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    item = await InventoryItemRepository(db_session).create(
        serial_number="SN-TRANSFER-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=source.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    preview = await api_client.get(f"/api/v1/locations/{source.id}/archive-preview", headers=admin_headers)
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["movable_inventory_count"] == 1
    assert preview_data["requires_transfer"] is True

    blocked = await api_client.post(f"/api/v1/locations/{source.id}/archive", headers=admin_headers, json={})
    assert blocked.status_code == 409

    archived = await api_client.post(
        f"/api/v1/locations/{source.id}/archive",
        headers=admin_headers,
        json={"transfer_to_location_id": destination.id},
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["is_active"] is False

    await db_session.refresh(item)
    assert item.current_location_id == destination.id


@pytest.mark.asyncio
async def test_brand_archive_cascades_product_models(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from decimal import Decimal

    from webstudio_backend.infrastructure.database.enums import ProductModelStatus, StorageType, StorageUnit
    from webstudio_backend.infrastructure.repositories import BrandRepository, ProductModelRepository

    brand = await BrandRepository(db_session).create("Cascade Brand")
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="CAS-01",
        model_name="Cascade Model",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()

    resp = await api_client.post(f"/api/v1/brands/{brand.id}/archive", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False

    await db_session.refresh(product_model)
    assert product_model.status is ProductModelStatus.ARCHIVED

