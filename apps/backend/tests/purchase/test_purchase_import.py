"""Purchase Import Queue + import API tests (additive feature).

Proves the feature end to end while guaranteeing no inventory is auto-created and
that failed imports leave nothing behind (transactional rollback semantics).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import InventorySource, InventoryStatus
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.services.inventory_service import InventoryService

pytestmark = pytest.mark.asyncio


async def test_queue_projection_lists_pending_voucher(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    response = await api_client.get("/api/v1/purchase/queue", headers=main_admin_headers)
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    item = items[0]
    assert item["supplier_name"] == "Acme Distributors"
    assert item["voucher_number"] == "66"
    assert item["status"] == "pending"
    assert item["group_count"] == 2
    assert item["imported_group_count"] == 0
    assert item["taxes"]["cgst_amount"] == "9000.00"


async def test_voucher_detail_groups_serials_and_duplicates(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    response = await api_client.get(
        f"/api/v1/purchase/queue/{purchase_voucher.id}", headers=main_admin_headers
    )
    assert response.status_code == 200
    detail = response.json()["data"]
    groups = {g["stock_item_name"]: g for g in detail["groups"]}
    laptop = groups["ASUS F1504FA-BQ2113WS"]
    assert laptop["quantity"] == 2
    assert [c["serial_number"] for c in laptop["serials"]] == ["SNPUR001", "SNPUR002"]
    assert all(c["is_duplicate"] is False for c in laptop["serials"])
    accessory = groups["ASUS Carry Case"]
    assert accessory["serials"] == []
    assert accessory["quantity"] == 2


async def test_match_model_auto_selects_existing_within_brand(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    product_model: ProductModel,
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/match-model",
        headers=main_admin_headers,
        json={"brand_id": brand.id, "model_number": "ASUS F1504FA-BQ2113WS"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["normalized_model_number"] == "F1504FA-BQ2113WS"
    assert len(data["matches"]) == 1
    assert data["auto_selected_model_id"] == str(product_model.id)


async def test_import_existing_appends_and_sets_inventory_source(
    db_session: AsyncSession,
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS F1504FA-BQ2113WS",
            "brand_id": brand.id,
            "mode": "existing",
            "product_model_id": str(product_model.id),
            "serial_numbers": ["SNPUR001", "SNPUR002"],
            "color": "Black",
            "current_location_id": location.id,
            "status": "available",
            "purchase_price": 50000,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["imported_count"] == 2
    assert body["existing_model"] is True

    repo = InventoryItemRepository(db_session)
    for serial in ("SNPUR001", "SNPUR002"):
        items = await repo.find_all_by_serial_number(serial)
        assert len(items) == 1
        assert items[0].inventory_source == InventorySource.TALLY_PURCHASE
        assert items[0].product_model_id == product_model.id

    # Accessory group still pending → voucher partially imported.
    detail = await api_client.get(
        f"/api/v1/purchase/queue/{purchase_voucher.id}", headers=main_admin_headers
    )
    assert detail.json()["data"]["status"] == "partially_imported"


async def test_import_new_model_creates_model_and_units(
    db_session: AsyncSession,
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS Carry Case",
            "brand_id": brand.id,
            "mode": "new",
            "new_product_model": {
                "brand_id": brand.id,
                "model_number": "CARRY-CASE-01",
                "model_name": "ASUS Carry Case",
                "cpu": "N/A",
                "ram_gb": 1,
                "storage_value": 1,
                "storage_unit": "GB",
                "storage_type": "SSD",
            },
            "serial_numbers": ["ACC001", "ACC002"],
            "color": "Black",
            "current_location_id": location.id,
            "status": "available",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["existing_model"] is False
    assert body["imported_count"] == 2

    repo = InventoryItemRepository(db_session)
    items = await repo.find_all_by_serial_number("ACC001")
    assert len(items) == 1
    assert items[0].inventory_source == InventorySource.TALLY_PURCHASE


async def test_duplicate_serial_is_rejected_with_no_partial_creation(
    db_session: AsyncSession,
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    admin_actor: AuditActor,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    # Pre-seed one of the incoming serials so it already exists in IMS.
    await InventoryService(db_session).create_item(
        serial_number="SNPUR001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
        actor=admin_actor,
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS F1504FA-BQ2113WS",
            "brand_id": brand.id,
            "mode": "existing",
            "product_model_id": str(product_model.id),
            "serial_numbers": ["SNPUR001", "SNPUR002"],
            "color": "Black",
            "current_location_id": location.id,
        },
    )
    assert response.status_code == 409

    repo = InventoryItemRepository(db_session)
    # The other (new) serial must NOT have been created.
    assert await repo.find_all_by_serial_number("SNPUR002") == []
    # Original one still present exactly once.
    assert len(await repo.find_all_by_serial_number("SNPUR001")) == 1


async def test_missing_serials_rejected(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS F1504FA-BQ2113WS",
            "brand_id": brand.id,
            "mode": "existing",
            "product_model_id": str(product_model.id),
            "serial_numbers": [],
            "color": "Black",
            "current_location_id": location.id,
        },
    )
    assert response.status_code == 422


async def test_already_imported_group_is_guarded(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    payload = {
        "voucher_id": purchase_voucher.id,
        "group_key": "ASUS F1504FA-BQ2113WS",
        "brand_id": brand.id,
        "mode": "existing",
        "product_model_id": str(product_model.id),
        "serial_numbers": ["SNPUR001", "SNPUR002"],
        "color": "Black",
        "current_location_id": location.id,
    }
    first = await api_client.post(
        "/api/v1/purchase/import", headers=main_admin_headers, json=payload
    )
    assert first.status_code == 200, first.text

    second = await api_client.post(
        "/api/v1/purchase/import", headers=main_admin_headers, json=payload
    )
    assert second.status_code == 409
