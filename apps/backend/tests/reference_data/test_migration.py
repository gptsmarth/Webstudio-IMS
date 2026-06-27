"""Alembic migration tests for reference data."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0002_reference_tables_exist(database_engine: None) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision in {"0002_reference_data", "0003_product_model"}

        def inspect_schema(sync_connection) -> tuple[list[str], list[str], list[str]]:
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names(schema="webstudio")
            brand_indexes = {
                index["name"] for index in inspector.get_indexes("brands", schema="webstudio")
            }
            brand_uniques = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("brands", schema="webstudio")
            }
            location_uniques = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("locations", schema="webstudio")
            }
            return tables, sorted(brand_indexes | brand_uniques), sorted(location_uniques)

        tables, brand_constraints, location_constraints = await connection.run_sync(
            lambda sync_connection: inspect_schema(sync_connection),
        )

    assert "brands" in tables
    assert "locations" in tables
    assert "uq_brands_name" in brand_constraints
    assert "uq_locations_name" in location_constraints
