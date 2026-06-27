"""Infrastructure probe table fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text

from infrastructure.models import InfrastructureProbe
from webstudio_backend.infrastructure.database.session import get_engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def infrastructure_probe_tables(database_engine: None) -> AsyncGenerator[None, None]:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS webstudio"))
        await connection.run_sync(
            lambda sync_connection: InfrastructureProbe.__table__.create(
                sync_connection,
                checkfirst=True,
            ),
        )
    yield
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: InfrastructureProbe.__table__.drop(
                sync_connection,
                checkfirst=True,
            ),
        )
