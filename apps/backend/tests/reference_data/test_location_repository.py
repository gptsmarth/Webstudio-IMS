"""Location repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import LocationType
from webstudio_backend.infrastructure.database.repositories import PageParams, SortParam
from webstudio_backend.infrastructure.repositories import (
    DuplicateNameError,
    LocationRepository,
    RequiredFieldError,
)


@pytest.mark.asyncio
async def test_location_repository_crud(db_session: AsyncSession) -> None:
    repository = LocationRepository(db_session)

    created = await repository.create("Warehouse", location_type=LocationType.WAREHOUSE)
    assert created.id is not None
    assert created.name == "Warehouse"
    assert created.location_type is LocationType.WAREHOUSE
    assert created.is_active is True

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None

    updated = await repository.update_name(loaded, "Main Warehouse")
    assert updated.name == "Main Warehouse"

    await repository.delete(updated)
    assert await repository.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_location_name_must_be_unique(db_session: AsyncSession) -> None:
    repository = LocationRepository(db_session)
    await repository.create("Store", location_type=LocationType.RETAIL_FLOOR)

    with pytest.raises(DuplicateNameError):
        await repository.create("Store", location_type=LocationType.OTHER)


@pytest.mark.asyncio
async def test_location_name_is_required(db_session: AsyncSession) -> None:
    repository = LocationRepository(db_session)

    with pytest.raises(RequiredFieldError):
        await repository.create("  ", location_type=LocationType.OTHER)


@pytest.mark.asyncio
async def test_location_pagination_and_sorting(db_session: AsyncSession) -> None:
    repository = LocationRepository(db_session)

    await repository.create("Service Area", location_type=LocationType.OTHER)
    await repository.create("Store", location_type=LocationType.RETAIL_FLOOR)
    await repository.create("Warehouse", location_type=LocationType.WAREHOUSE)

    page = await repository.list_all(
        PageParams(page=1, page_size=2),
        sort_params=[SortParam(field="name", direction="asc")],
    )

    assert page.total_items >= 3
    assert len(page.items) == 2
    assert page.items[0].name <= page.items[1].name
