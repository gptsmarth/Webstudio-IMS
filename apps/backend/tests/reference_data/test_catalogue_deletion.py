"""Catalogue entity deletion tests — dependency validation, transfer, history preservation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    SaleSource,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
)


@pytest.mark.asyncio
async def test_brand_delete_blocked_with_dependencies(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand = await BrandRepository(db_session).create("Blocked Brand")
    await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="BLK-01",
        model_name="Blocked Model",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()

    preview = await api_client.get(
        f"/api/v1/brands/{brand.id}/delete-preview", headers=admin_headers
    )
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["product_model_count"] == 1
    assert preview_data["can_delete"] is False

    resp = await api_client.delete(f"/api/v1/brands/{brand.id}", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CATALOGUE_DELETE_BLOCKED"


@pytest.mark.asyncio
async def test_brand_delete_succeeds_when_empty(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand = await BrandRepository(db_session).create("Empty Brand")
    await db_session.commit()

    resp = await api_client.delete(f"/api/v1/brands/{brand.id}", headers=admin_headers)
    assert resp.status_code == 204
    assert await BrandRepository(db_session).get_by_id(brand.id) is None


@pytest.mark.asyncio
async def test_product_model_delete_cascades_inventory_and_preserves_sales(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand = await BrandRepository(db_session).create("Model Cascade Brand")
    location = await LocationRepository(db_session).create(
        "Model Cascade Loc", location_type=LocationType.WAREHOUSE
    )
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="MC-01",
        model_name="Model Cascade",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await InventoryItemRepository(db_session).create(
        serial_number="SN-MODEL-CASCADE-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    preview = await api_client.get(
        f"/api/v1/product-models/{product_model.id}/delete-preview",
        headers=admin_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["data"]["inventory_count"] == 1
    assert preview.json()["data"]["can_delete"] is True

    resp = await api_client.delete(
        f"/api/v1/product-models/{product_model.id}", headers=admin_headers
    )
    assert resp.status_code == 204
    assert await ProductModelRepository(db_session).get_by_id(product_model.id) is None


@pytest.mark.asyncio
async def test_location_delete_preview_and_transfer(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand = await BrandRepository(db_session).create("Transfer Brand")
    source = await LocationRepository(db_session).create(
        "Source Loc", location_type=LocationType.WAREHOUSE
    )
    destination = await LocationRepository(db_session).create(
        "Dest Loc", location_type=LocationType.RETAIL_FLOOR
    )
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

    preview = await api_client.get(
        f"/api/v1/locations/{source.id}/delete-preview", headers=admin_headers
    )
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["inventory_count"] == 1
    assert preview_data["movable_inventory_count"] == 1
    assert preview_data["requires_transfer"] is True

    blocked = await api_client.request(
        "DELETE",
        f"/api/v1/locations/{source.id}",
        headers=admin_headers,
        json={},
    )
    assert blocked.status_code == 409

    deleted = await api_client.request(
        "DELETE",
        f"/api/v1/locations/{source.id}",
        headers=admin_headers,
        json={"transfer_to_location_id": destination.id},
    )
    assert deleted.status_code == 204

    await db_session.refresh(item)
    assert item.current_location_id == destination.id
    assert await LocationRepository(db_session).get_by_id(source.id) is None


@pytest.mark.asyncio
async def test_location_delete_preserves_tally_sales_with_mapped_location(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    source = await LocationRepository(db_session).create(
        "Tally Source", location_type=LocationType.RETAIL_FLOOR
    )
    sale = Sale(
        inventory_item_id=None,
        sale_source=SaleSource.TALLY,
        sold_at=datetime.now(UTC),
        invoice_number="TALLY-LOC-001",
        mapped_location_id=source.id,
        snapshot_location_name=None,
        snapshot_brand_name="HP",
        snapshot_model_number="840-G8",
    )
    db_session.add(sale)
    await db_session.commit()
    sale_id = sale.id

    deleted = await api_client.delete(f"/api/v1/locations/{source.id}", headers=admin_headers)
    assert deleted.status_code == 204

    db_session.expire_all()
    persisted = await db_session.get(Sale, sale_id)
    assert persisted is not None
    assert persisted.snapshot_location_name == "Tally Source"
    assert persisted.mapped_location_id is None


@pytest.mark.asyncio
async def test_deleted_entities_preserve_sales_and_audit_history(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brand = await BrandRepository(db_session).create("History Brand")
    location = await LocationRepository(db_session).create(
        "History Loc", location_type=LocationType.WAREHOUSE
    )
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="HIST-01",
        model_name="History Model",
        cpu="Intel i5",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    item = await InventoryItemRepository(db_session).create(
        serial_number="SN-HIST-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    sale = Sale(
        inventory_item_id=item.id,
        sale_source=SaleSource.MANUAL,
        sold_at=datetime.now(UTC),
        invoice_number="INV-HIST-001",
        snapshot_serial_number=item.serial_number,
        snapshot_product_model_id=product_model.id,
        snapshot_brand_id=brand.id,
        snapshot_brand_name=brand.name,
        snapshot_model_number=product_model.model_number,
        snapshot_model_name=product_model.model_name,
        snapshot_location_name=location.name,
    )
    db_session.add(sale)
    await db_session.commit()
    sale_id = sale.id
    item_id = item.id

    resp = await api_client.delete(
        f"/api/v1/product-models/{product_model.id}", headers=admin_headers
    )
    assert resp.status_code == 204

    persisted_sale = await db_session.get(Sale, sale_id)
    assert persisted_sale is not None
    assert persisted_sale.inventory_item_id is None
    assert persisted_sale.snapshot_brand_name == "History Brand"
    assert persisted_sale.snapshot_model_number == "HIST-01"
    assert persisted_sale.snapshot_serial_number == "SN-HIST-001"
    assert await InventoryItemRepository(db_session).get_by_id(item_id) is None

    audit_rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "product_model",
                    AuditLog.entity_id == str(product_model.id),
                ),
            )
        )
        .scalars()
        .all()
    )
    assert audit_rows
