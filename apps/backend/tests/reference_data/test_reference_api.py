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

    # 6. Delete brand (permanent)
    resp = await api_client.delete(f"/api/v1/brands/{brand_id}", headers=admin_headers)
    assert resp.status_code == 204

    resp = await api_client.get(f"/api/v1/brands/{brand_id}", headers=salesperson_headers)
    assert resp.status_code == 404


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

    # 6. Delete empty location
    resp = await api_client.delete(f"/api/v1/locations/{loc_id}", headers=admin_headers)
    assert resp.status_code == 204

    resp = await api_client.get(f"/api/v1/locations/{loc_id}", headers=salesperson_headers)
    assert resp.status_code == 404
