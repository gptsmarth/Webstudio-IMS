"""ORM mixin tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import InfrastructureProbe
from webstudio_backend.infrastructure.database.repositories import SqlAlchemyRepository


@pytest.mark.asyncio
async def test_base_model_sets_timestamps(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRepository(db_session, InfrastructureProbe)
    entity = await repository.add(InfrastructureProbe(label="timestamp-test"))

    assert entity.id is not None
    assert entity.created_at is not None
    assert entity.updated_at is not None
