"""Reference data seed tests."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.seed.reference_data import (
    DEFAULT_BRANDS,
    DEFAULT_LOCATIONS,
    seed_reference_data,
)


@pytest.mark.asyncio
async def test_seed_reference_data_is_idempotent(db_session: AsyncSession) -> None:
    first = await seed_reference_data(db_session)
    assert first.brands_created == len(DEFAULT_BRANDS)
    assert first.locations_created == len(DEFAULT_LOCATIONS)

    second = await seed_reference_data(db_session)
    assert second.brands_created == 0
    assert second.locations_created == 0

    brand_count = await db_session.scalar(select(func.count()).select_from(Brand))
    location_count = await db_session.scalar(select(func.count()).select_from(Location))

    assert brand_count == len(DEFAULT_BRANDS)
    assert location_count == len(DEFAULT_LOCATIONS)

    brand_names = (await db_session.scalars(select(Brand.name).order_by(Brand.name))).all()
    assert list(brand_names) == sorted(DEFAULT_BRANDS)

    location_names = (await db_session.scalars(select(Location.name).order_by(Location.name))).all()
    assert list(location_names) == sorted(name for name, _ in DEFAULT_LOCATIONS)
