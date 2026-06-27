"""Inventory movement migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_migration_0005_inventory_movements_exist(db_session: AsyncSession) -> None:
    current_revision = await db_session.scalar(
        text("SELECT version_num FROM webstudio.alembic_version"),
    )
    assert current_revision == "0005_inventory_movement"

    connection = await db_session.connection()

    def inspect_schema(sync_connection) -> tuple[list[str], set[str], set[str]]:
        inspector = inspect(sync_connection)
        tables = inspector.get_table_names(schema="webstudio")
        indexes = {
            index["name"]
            for index in inspector.get_indexes("inventory_movements", schema="webstudio")
        }
        checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints(
                "inventory_movements",
                schema="webstudio",
            )
        }
        return tables, indexes, checks

    tables, indexes, checks = await connection.run_sync(inspect_schema)

    assert "inventory_movements" in tables
    assert "audit_logs" not in tables
    assert "users" not in tables
    assert {
        "ix_inventory_movements_inventory_item_id",
        "ix_inventory_movements_from_location_id",
        "ix_inventory_movements_to_location_id",
        "ix_inventory_movements_moved_at",
        "ix_inventory_movements_movement_reason",
    }.issubset(indexes)
    assert any("diff_locs" in name for name in checks)


# Downgrade verified manually: `alembic downgrade 0004_inventory_item` then `upgrade head`
