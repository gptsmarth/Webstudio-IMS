"""Product model test isolation and fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import StorageType, StorageUnit
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories import BrandRepository


@pytest_asyncio.fixture(autouse=True)
async def clean_product_model_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.product_models, webstudio.brands " "RESTART IDENTITY CASCADE",
        ),
    )


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession) -> Brand:
    return await BrandRepository(db_session).create("ASUS")


def sample_product_model_payload(brand_id: int) -> dict[str, object]:
    return {
        "brand_id": brand_id,
        "model_number": "X1502ZA-EJ541WS",
        "model_name": "Vivobook 15",
        "cpu": "Intel Core i5-1235U",
        "gpu": "Intel Iris Xe",
        "ram_gb": 16,
        "storage_value": Decimal("512"),
        "storage_unit": StorageUnit.GB,
        "storage_type": StorageType.SSD,
    }
