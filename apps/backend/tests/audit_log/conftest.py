"""Audit log test fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit import AuditActor
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

ADMIN_ACTOR = AuditActor(user_id=1, display_name="Admin User", role="admin")


@pytest_asyncio.fixture(autouse=True)
async def clean_audit_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.audit_logs, webstudio.inventory_items, "
            "webstudio.product_models, webstudio.locations, webstudio.brands "
            "RESTART IDENTITY CASCADE",
        ),
    )


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession) -> Brand:
    return await BrandRepository(db_session).create("ASUS", actor=ADMIN_ACTOR)


@pytest_asyncio.fixture
async def warehouse(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
        actor=ADMIN_ACTOR,
    )


@pytest_asyncio.fixture
async def store(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "ASUS Store",
        location_type=LocationType.RETAIL_FLOOR,
        actor=ADMIN_ACTOR,
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
        actor=ADMIN_ACTOR,
    )


@pytest_asyncio.fixture
async def inventory_item(
    db_session: AsyncSession,
    product_model: ProductModel,
    warehouse: Location,
):
    return await InventoryItemRepository(db_session).create(
        serial_number="SN-LIFECYCLE-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=warehouse.id,
        status=InventoryStatus.AVAILABLE,
        actor=ADMIN_ACTOR,
    )
