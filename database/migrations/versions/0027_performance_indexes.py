"""Milestone 9B — query performance indexes for reports, audit, notifications, sales."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_performance_indexes"
down_revision: str | None = "0026_backup_enterprise"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_index(
        "ix_inventory_items_created_at",
        "inventory_items",
        [sa.text("created_at DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sales_recorded_by_user_id",
        "sales",
        ["recorded_by_user_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_inbox",
        "notifications",
        ["is_resolved", "is_read", sa.text("created_at DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_inventory_item_id",
        "notifications",
        ["inventory_item_id"],
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_audit_logs_new_value_gin
            ON {SCHEMA}.audit_logs
            USING gin (new_value jsonb_path_ops)
            """,
        ),
    )
    op.create_index(
        "ix_audit_logs_created_entity",
        "audit_logs",
        ["created_at", "entity_type"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_entity", table_name="audit_logs", schema=SCHEMA)
    op.execute(sa.text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_logs_new_value_gin"))
    op.drop_index("ix_notifications_inventory_item_id", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_notifications_inbox", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_sales_recorded_by_user_id", table_name="sales", schema=SCHEMA)
    op.drop_index("ix_inventory_items_created_at", table_name="inventory_items", schema=SCHEMA)
