"""Audit log migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0005_audit_logs_exist(db_session) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision == "0008_users_authentication"

        def inspect_schema(sync_connection) -> tuple[list[str], set[str]]:
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names(schema="webstudio")
            indexes = {
                index["name"]
                for index in inspector.get_indexes("audit_logs", schema="webstudio")
            }
            return tables, indexes

        tables, indexes = await connection.run_sync(inspect_schema)

    assert "audit_logs" in tables
    for expected in (
        "ix_audit_logs_entity_type",
        "ix_audit_logs_entity_id",
        "ix_audit_logs_inventory_item_id",
        "ix_audit_logs_actor_user_id",
        "ix_audit_logs_action",
        "ix_audit_logs_created_at",
        "ix_audit_logs_source",
    ):
        assert expected in indexes
