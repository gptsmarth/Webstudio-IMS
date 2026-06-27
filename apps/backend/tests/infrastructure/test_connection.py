"""Database connectivity tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_database_connection(database_engine: None) -> None:
    engine = get_engine()
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
