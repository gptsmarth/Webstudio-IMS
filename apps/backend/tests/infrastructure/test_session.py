"""Session lifecycle tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import InfrastructureProbe
from webstudio_backend.infrastructure.database.repositories import SqlAlchemyRepository


@pytest.mark.asyncio
async def test_session_persists_entity(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRepository(db_session, InfrastructureProbe)
    created = await repository.add(InfrastructureProbe(label="session-test"))
    assert created.id is not None

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.label == "session-test"
