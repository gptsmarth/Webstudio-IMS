"""Notification migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0013_notifications(db_session) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision == "0013_notifications"

        def inspect_schema(sync_connection) -> tuple[list[str], set[str]]:
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names(schema="webstudio")
            indexes = {
                index["name"]
                for index in inspector.get_indexes("notifications", schema="webstudio")
            }
            return tables, indexes

        tables, indexes = await connection.run_sync(inspect_schema)

    assert "notifications" in tables
    assert {
        "ix_notifications_notification_type",
        "ix_notifications_category",
        "ix_notifications_is_read",
        "ix_notifications_is_resolved",
        "ix_notifications_created_at",
    }.issubset(indexes)
