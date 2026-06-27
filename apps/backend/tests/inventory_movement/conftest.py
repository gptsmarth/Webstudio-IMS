"""Inventory movement test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    MovementReason,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
)


@pytest_asyncio.fixture(autouse=True)
async def clean_movement_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.inventory_movements, webstudio.inventory_items, "
            "webstudio.product_models, webstudio.locations, webstudio.brands "
            "RESTART IDENTITY CASCADE",
        ),
    )


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession) -> Brand:
    return await BrandRepository(db_session).create("ASUS")


@pytest_asyncio.fixture
async def from_location(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
    )


@pytest_asyncio.fixture
async def to_location(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "ASUS Exclusive Store",
        location_type=LocationType.RETAIL_FLOOR,
    )


@pytest_asyncio.fixture
async def product_model(db_session: AsyncSession, brand: Brand) -> ProductModel:
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


@pytest_asyncio.fixture
async def inventory_item(
    db_session: AsyncSession,
    product_model: ProductModel,
    from_location: Location,
) -> InventoryItem:
    return await InventoryItemRepository(db_session).create(
        serial_number="SN-MOVE-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=from_location.id,
        status=InventoryStatus.AVAILABLE,
    )


def sample_movement_payload(
    *,
    inventory_item_id,
    from_location_id: int,
    to_location_id: int,
    movement_reason: MovementReason = MovementReason.STORE_TRANSFER,
    moved_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "inventory_item_id": inventory_item_id,
        "from_location_id": from_location_id,
        "to_location_id": to_location_id,
        "movement_reason": movement_reason,
        "moved_at": moved_at or datetime(2026, 6, 27, 10, 0, tzinfo=UTC),
    }
