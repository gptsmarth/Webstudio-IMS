"""Brand repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.repositories import PageParams, SortParam
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    DuplicateNameError,
    RequiredFieldError,
)


@pytest.mark.asyncio
async def test_brand_repository_crud(db_session: AsyncSession) -> None:
    repository = BrandRepository(db_session)

    created = await repository.create("ASUS")
    assert created.id is not None
    assert created.name == "ASUS"
    assert created.is_active is True
    assert created.created_at is not None

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.name == "ASUS"

    updated = await repository.update_name(loaded, "ASUS ROG")
    assert updated.name == "ASUS ROG"

    await repository.delete(updated)
    assert await repository.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_brand_name_must_be_unique(db_session: AsyncSession) -> None:
    repository = BrandRepository(db_session)
    await repository.create("Lenovo")

    with pytest.raises(DuplicateNameError):
        await repository.create("Lenovo")


@pytest.mark.asyncio
async def test_brand_name_is_required(db_session: AsyncSession) -> None:
    repository = BrandRepository(db_session)

    with pytest.raises(RequiredFieldError):
        await repository.create("   ")


@pytest.mark.asyncio
async def test_brand_pagination_and_sorting(db_session: AsyncSession) -> None:
    repository = BrandRepository(db_session)

    for name in ("HP", "Acer", "Dell"):
        await repository.create(name)

    page = await repository.list_all(
        PageParams(page=1, page_size=2),
        sort_params=[SortParam(field="name", direction="asc")],
    )

    assert page.total_items >= 3
    assert len(page.items) == 2
    assert page.items[0].name <= page.items[1].name
