"""ProductModel API tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository


@pytest.mark.asyncio
async def test_product_model_rbac_and_crud(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
    admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
) -> None:
    # 1. Create seed Brand
    brand_repo = BrandRepository(db_session)
    brand_asus = await brand_repo.create("ASUS")
    brand_dell = await brand_repo.create("Dell")
    await db_session.commit()

    brand_id_asus = brand_asus.id
    brand_id_dell = brand_dell.id

    # 2. Read access
    # Unauthorized
    resp = await api_client.get("/api/v1/product-models")
    assert resp.status_code == 401

    # Salesperson can read (empty list)
    resp = await api_client.get("/api/v1/product-models", headers=salesperson_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []

    # 3. Create Product Model
    payload = {
        "brand_id": brand_id_asus,
        "model_number": "X1502ZA",
        "model_name": "Vivobook 15",
        "cpu": "Intel Core i5",
        "gpu": "Intel Iris Xe",
        "ram_gb": 16,
        "storage_value": 512,
        "storage_unit": "GB",
        "storage_type": "SSD",
        "display": "15.6 FHD",
        "color_options": "Quiet Blue",
        "product_image_url": "http://img.com/asus.png",
        "search_aliases": "Vivobook, Asus 15",
        "notes": "Premium laptop",
    }

    # Salesperson forbidden
    resp = await api_client.post(
        "/api/v1/product-models", json=payload, headers=salesperson_headers
    )
    assert resp.status_code == 403

    # Admin allowed
    resp = await api_client.post("/api/v1/product-models", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    pm_data = resp.json()["data"]
    assert pm_data["model_name"] == "Vivobook 15"
    assert pm_data["display"] == "15.6 FHD"
    assert pm_data["color_options"] == "Quiet Blue"
    assert pm_data["brand_name"] == "ASUS"
    pm_id = pm_data["id"]

    # 4. Prevent duplicate model number under same brand
    resp = await api_client.post("/api/v1/product-models", json=payload, headers=admin_headers)
    assert resp.status_code == 409

    # Same model number under different brand is allowed
    payload_dell = payload.copy()
    payload_dell["brand_id"] = brand_id_dell
    resp = await api_client.post("/api/v1/product-models", json=payload_dell, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["brand_name"] == "Dell"

    # 5. GET detail
    resp = await api_client.get(f"/api/v1/product-models/{pm_id}", headers=salesperson_headers)
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["model_name"] == "Vivobook 15"
    assert detail["brand_name"] == "ASUS"

    # GET detail not found
    resp = await api_client.get(
        f"/api/v1/product-models/{uuid.uuid4()}", headers=salesperson_headers
    )
    assert resp.status_code == 404

    # 6. PATCH Product Model
    update_payload = {
        "model_name": "Vivobook 15 Pro",
        "display": "15.6 OLED",
    }
    resp = await api_client.patch(
        f"/api/v1/product-models/{pm_id}", json=update_payload, headers=admin_headers
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["model_name"] == "Vivobook 15 Pro"
    assert updated["display"] == "15.6 OLED"

    # 7. List and filtering
    # Active only
    resp = await api_client.get("/api/v1/product-models?active=true", headers=salesperson_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2

    # Filtering by brand
    resp = await api_client.get(
        f"/api/v1/product-models?brand_id={brand_id_dell}", headers=salesperson_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["brand_name"] == "Dell"

    # 8. Permanent delete (Admin allowed)
    resp = await api_client.delete(f"/api/v1/product-models/{pm_id}", headers=admin_headers)
    assert resp.status_code == 204

    # Deleted model no longer appears in list
    resp = await api_client.get("/api/v1/product-models?active=true", headers=salesperson_headers)
    assert len(resp.json()["data"]) == 1
    assert all(row["id"] != pm_id for row in resp.json()["data"])

    resp = await api_client.get(f"/api/v1/product-models/{pm_id}", headers=salesperson_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_product_model_validates_brand(
    api_client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    brand_repo = BrandRepository(db_session)
    brand_archived = await brand_repo.create("Archived Brand", is_active=False)
    await db_session.commit()

    payload = {
        "brand_id": brand_archived.id,
        "model_number": "MODEL-X",
        "model_name": "Model X",
        "cpu": "Core i7",
        "ram_gb": 8,
        "storage_value": 256,
        "storage_unit": "GB",
        "storage_type": "SSD",
    }

    # Creating a model under a deleted/inactive brand should fail
    resp = await api_client.post("/api/v1/product-models", json=payload, headers=admin_headers)
    assert resp.status_code == 404
    assert "not available" in resp.json()["error"]["message"].lower()

    # Creating under a non-existent brand should fail
    payload["brand_id"] = 99999
    resp = await api_client.post("/api/v1/product-models", json=payload, headers=admin_headers)
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_create_product_model_normalizes_optional_payload_fields(
    api_client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.create("Lenovo")
    await db_session.commit()

    long_image_url = "https://example.com/" + ("a" * 600)
    payload = {
        "brand_id": brand.id,
        "model_number": "82VG00XXIN",
        "model_name": "IdeaPad Slim 3",
        "cpu": "Intel Core i5",
        "gpu": "",
        "ram_gb": 16,
        "storage_value": 512,
        "storage_unit": "GB",
        "storage_type": "SSD",
        "display": "  ",
        "color_options": "",
        "product_image_url": long_image_url,
        "search_aliases": "",
        "notes": "",
    }

    resp = await api_client.post("/api/v1/product-models", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    pm_data = resp.json()["data"]
    assert pm_data["gpu"] is None
    assert pm_data["display"] is None
    assert pm_data["product_image_url"] is None
