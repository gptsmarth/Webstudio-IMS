"""Product model migration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from webstudio_backend.infrastructure.database.session import get_engine


@pytest.mark.asyncio
async def test_migration_0003_product_models_exist(database_engine: None) -> None:
    engine = get_engine()

    async with engine.connect() as connection:
        current_revision = await connection.scalar(
            text("SELECT version_num FROM webstudio.alembic_version"),
        )
        assert current_revision in {
            "0003_product_model",
            "0004_inventory_item",
            "0005_audit_logs",
            "0006_audit_log_description",
            "0007_audit_log_source",
            "0010_inventory_sprint_2a",
        }

        def inspect_schema(sync_connection) -> tuple[list[str], set[str], set[str]]:
            inspector = inspect(sync_connection)
            tables = inspector.get_table_names(schema="webstudio")
            indexes = {
                index["name"]
                for index in inspector.get_indexes("product_models", schema="webstudio")
            }
            uniques = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(
                    "product_models",
                    schema="webstudio",
                )
            }
            return tables, indexes, uniques

        tables, indexes, uniques = await connection.run_sync(
            lambda sync_connection: inspect_schema(sync_connection),
        )

    assert "product_models" in tables
    assert "uq_product_models_brand_model_number" in uniques
    assert {
        "ix_product_models_brand_id",
        "ix_product_models_status",
        "ix_product_models_model_number",
        "ix_product_models_model_name",
    }.issubset(indexes)
