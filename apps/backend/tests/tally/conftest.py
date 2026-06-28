"""Tally integration test fixtures."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import LocationType, StorageType, StorageUnit
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories import BrandRepository, LocationRepository, ProductModelRepository


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession) -> Brand:
    return await BrandRepository(db_session).create("ASUS")


@pytest_asyncio.fixture
async def location(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
    )


@pytest_asyncio.fixture
async def product_model(db_session: AsyncSession, brand: Brand) -> ProductModel:
    return await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="X1502ZA-EJ541WS",
        model_name="Vivobook 15",
        cpu="Intel Core i5-1235U",
        ram_gb=16,
        storage_value=512,
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
