"""Inventory item migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0004_inventory_items_exist(database_engine: None) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision == "0004_inventory_item"

        def inspect_schema(sync_connection) -> tuple[list[str], set[str], set[str]]:
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names(schema="webstudio")
            indexes = {
                index["name"]
                for index in inspector.get_indexes("inventory_items", schema="webstudio")
            }
            uniques = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(
                    "inventory_items",
                    schema="webstudio",
                )
            }
            return tables, indexes, uniques

        tables, indexes, uniques = await connection.run_sync(
            lambda sync_connection: inspect_schema(sync_connection),
        )

    assert "inventory_items" in tables
    assert "inventory_movements" not in tables
    assert "uq_inventory_items_serial_number" in uniques
    assert {
        "ix_inventory_items_product_model_id",
        "ix_inventory_items_current_location_id",
        "ix_inventory_items_status",
        "ix_inventory_items_color",
    }.issubset(indexes)
