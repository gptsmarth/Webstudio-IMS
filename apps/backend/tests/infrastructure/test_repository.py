"""Generic repository infrastructure tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import InfrastructureProbe
from webstudio_backend.infrastructure.database.repositories import (
    PageParams,
    SortParam,
    SqlAlchemyRepository,
)


@pytest.mark.asyncio
async def test_repository_crud(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRepository(db_session, InfrastructureProbe)

    alpha = await repository.add(InfrastructureProbe(label="alpha"))
    beta = await repository.add(InfrastructureProbe(label="beta"))

    loaded = await repository.get_by_id(alpha.id)
    assert loaded is not None
    assert loaded.label == "alpha"

    await repository.delete(beta)
    assert await repository.get_by_id(beta.id) is None


@pytest.mark.asyncio
async def test_repository_pagination_and_sorting(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRepository(db_session, InfrastructureProbe)

    for label in ("charlie", "alpha", "bravo"):
        await repository.add(InfrastructureProbe(label=label))

    page = await repository.list_all(
        PageParams(page=1, page_size=2),
        sort_params=[SortParam(field="label", direction="asc")],
    )

    assert page.total_items >= 3
    assert page.page == 1
    assert page.page_size == 2
    assert len(page.items) == 2
    assert page.items[0].label <= page.items[1].label
