"""Create notifications table for Notification Center."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_notifications"
down_revision: str | None = "0012_inventory_performance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

notification_type_enum = postgresql.ENUM(
    "duplicate_sale",
    "serial_number_missing",
    "product_model_missing",
    "tally_sync_completed",
    "sync_failure",
    "inventory_alert",
    "system_notification",
    name="notification_type",
    schema=SCHEMA,
    create_type=False,
)

notification_category_enum = postgresql.ENUM(
    "tally_sync",
    "inventory",
    "system",
    name="notification_category",
    schema=SCHEMA,
    create_type=False,
)

notification_severity_enum = postgresql.ENUM(
    "info",
    "warning",
    "error",
    name="notification_severity",
    schema=SCHEMA,
    create_type=False,
)

notification_creator_enum = postgresql.ENUM(
    "system",
    "user",
    name="notification_creator",
    schema=SCHEMA,
    create_type=False,
)


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA}.{enum_name} AS ENUM ({quoted_values});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """),
    )


def upgrade() -> None:
    _create_enum(
        "notification_type",
        (
            "duplicate_sale",
            "serial_number_missing",
            "product_model_missing",
            "tally_sync_completed",
            "sync_failure",
            "inventory_alert",
            "system_notification",
        ),
    )
    _create_enum("notification_category", ("tally_sync", "inventory", "system"))
    _create_enum("notification_severity", ("info", "warning", "error"))
    _create_enum("notification_creator", ("system", "user"))

    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("category", notification_category_enum, nullable=False),
        sa.Column("severity", notification_severity_enum, nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_by", notification_creator_enum, nullable=False, server_default="system"),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_number", sa.String(length=128), nullable=True),
        sa.Column("tally_company_name", sa.String(length=256), nullable=True),
        sa.Column("tally_voucher_number", sa.String(length=128), nullable=True),
        sa.Column("voucher_type", sa.String(length=64), nullable=True),
        sa.Column("customer_name", sa.String(length=256), nullable=True),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("product_model_number", sa.String(length=128), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            [f"{SCHEMA}.inventory_items.id"],
            name="fk_notifications_inventory_item",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_notifications_created_by_user",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_notifications_resolved_by_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_category",
        "notifications",
        ["category"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_is_read",
        "notifications",
        ["is_read"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_is_resolved",
        "notifications",
        ["is_resolved"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        [sa.text("created_at DESC")],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_notifications_is_resolved", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_notifications_is_read", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_notifications_category", table_name="notifications", schema=SCHEMA)
    op.drop_index("ix_notifications_notification_type", table_name="notifications", schema=SCHEMA)
    op.drop_table("notifications", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.notification_creator"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.notification_severity"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.notification_category"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.notification_type"))
