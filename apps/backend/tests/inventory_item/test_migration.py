"""Inventory item migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_migration_0004_inventory_items_exist(db_session: AsyncSession) -> None:
    current_revision = await db_session.scalar(
        text("SELECT version_num FROM webstudio.alembic_version"),
    )
    assert current_revision in {
        "0004_inventory_item",
        "0005_audit_logs",
        "0006_audit_log_description",
        "0007_audit_log_source",
        "0009_main_admin_recovery_key",
        "0010_inventory_sprint_2a",
        "0011_sales",
        "0013_notifications",
    }

    connection = await db_session.connection()

    def inspect_schema(sync_connection) -> tuple[list[str], set[str]]:
        inspector = inspect(sync_connection)
        tables = inspector.get_table_names(schema="webstudio")
        indexes = {
            index["name"]
            for index in inspector.get_indexes("inventory_items", schema="webstudio")
        }
        return tables, indexes

    tables, indexes = await connection.run_sync(inspect_schema)

    assert "inventory_items" in tables
    assert {
        "ix_inventory_items_product_model_id",
        "ix_inventory_items_current_location_id",
        "ix_inventory_items_status",
        "ix_inventory_items_color",
    }.issubset(indexes)
