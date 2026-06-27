"""Shared fixtures for database infrastructure tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import InfrastructureProbe
from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.database.session import (
    close_db,
    get_engine,
    get_session_factory,
    init_db,
)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return get_settings()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def database_engine(test_settings: Settings) -> AsyncGenerator[None, None]:
    await init_db(test_settings)
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS webstudio"))
        await connection.run_sync(InfrastructureProbe.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(InfrastructureProbe.metadata.drop_all)
    await close_db()


@pytest_asyncio.fixture
async def db_session(database_engine: None) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()
