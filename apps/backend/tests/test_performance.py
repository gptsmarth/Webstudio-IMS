"""Performance regression tests for Milestone 9B optimizations."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.tally_sync_log_repository import (
    TallySyncLogRepository,
)


@pytest.mark.asyncio
async def test_performance_indexes_exist_9b(db_session: AsyncSession) -> None:
    tables = {
        "inventory_items": {
            "ix_inventory_items_created_at",
        },
        "sales": {
            "ix_sales_recorded_by_user_id",
        },
        "notifications": {
            "ix_notifications_inbox",
            "ix_notifications_inventory_item_id",
        },
        "audit_logs": {
            "ix_audit_logs_new_value_gin",
            "ix_audit_logs_created_entity",
        },
    }
    for table_name, expected_indexes in tables.items():
        result = await db_session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'webstudio'
                  AND tablename = :table_name
                """,
            ),
            {"table_name": table_name},
        )
        index_names = {row[0] for row in result.all()}
        for index_name in expected_indexes:
            assert index_name in index_names, f"missing {index_name} on {table_name}"


@pytest.mark.asyncio
async def test_tally_aggregate_stats_uses_sql_sum(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = TallySyncLogRepository(db_session)
    captured: dict[str, object] = {}

    async def fake_execute(statement):
        captured["statement"] = statement
        return type("Result", (), {"one": lambda self: type("Row", (), {
            "invoices_processed": 0,
            "successfully_updated": 0,
            "already_sold": 0,
            "missing_serial": 0,
            "missing_model": 0,
            "model_mismatches": 0,
            "ignored_items": 0,
        })()})()

    monkeypatch.setattr(db_session, "execute", fake_execute)
    stats = await repo.aggregate_stats(company_sync_id=1)
    assert stats["invoices_processed"] == 0
    sql = str(captured["statement"])
    assert "sum" in sql.lower()
