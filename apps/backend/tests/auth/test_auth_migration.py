"""User authentication migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0008_users_authentication(db_session) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision == "0008_users_authentication"

        def inspect_schema(sync_connection) -> list[str]:
            inspector = inspect(sync_connection)
            return inspector.get_table_names(schema="webstudio")

        tables = await connection.run_sync(inspect_schema)

    for table in ("users", "refresh_tokens", "system_settings"):
        assert table in tables
