"""Create sales table for manual and Tally sale reflection."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_sales"
down_revision: str | None = "0010_inventory_sprint_2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

sale_source_enum = postgresql.ENUM(
    "tally",
    "manual",
    name="sale_source",
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
    _create_enum("sale_source", ("tally", "manual"))

    op.create_table(
        "sales",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_source", sale_source_enum, nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=128), nullable=False),
        sa.Column("recorded_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_name", sa.String(length=256), nullable=True),
        sa.Column("payment_mode", sa.String(length=64), nullable=True),
        sa.Column("tally_company_name", sa.String(length=256), nullable=True),
        sa.Column("tally_voucher_number", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            [f"{SCHEMA}.inventory_items.id"],
            name="fk_sales_inventory_item",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_sales_recorded_by_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
        sa.UniqueConstraint("inventory_item_id", name="uq_sales_inventory_item_id"),
        schema=SCHEMA,
    )

    op.create_index("ix_sales_sold_at", "sales", ["sold_at"], schema=SCHEMA)
    op.create_index("ix_sales_invoice_number", "sales", ["invoice_number"], schema=SCHEMA)
    op.create_index(
        "uq_sales_manual_invoice_item",
        "sales",
        ["invoice_number", "inventory_item_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("sale_source = 'manual'"),
    )


def downgrade() -> None:
    op.drop_index("uq_sales_manual_invoice_item", table_name="sales", schema=SCHEMA)
    op.drop_index("ix_sales_invoice_number", table_name="sales", schema=SCHEMA)
    op.drop_index("ix_sales_sold_at", table_name="sales", schema=SCHEMA)
    op.drop_table("sales", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.sale_source"))
