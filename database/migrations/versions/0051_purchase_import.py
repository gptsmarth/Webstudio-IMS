"""Purchase Import Module (additive): purchase queue + inventory_source metadata.

Revision ID: 0051_purchase_import
Revises: 0050_model_delete_cascade_fks

Adds:
  * webstudio.inventory_source enum + inventory_items.inventory_source column
    (server default 'manual' so every existing row is unchanged).
  * webstudio.tally_purchase_status enum.
  * webstudio.tally_purchase_voucher (Purchase Import Queue header).
  * webstudio.tally_purchase_line (one row per Tally inventory entry).

This migration NEVER touches the Sales sync tables, the GUID watermark, or any
existing business column. It is purely additive.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051_purchase_import"
down_revision: str | None = "0050_model_delete_cascade_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


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


inventory_source_enum = postgresql.ENUM(
    "manual",
    "tally_purchase",
    name="inventory_source",
    schema=SCHEMA,
    create_type=False,
)

tally_purchase_status_enum = postgresql.ENUM(
    "pending",
    "partially_imported",
    "imported",
    name="tally_purchase_status",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    _create_enum("inventory_source", ("manual", "tally_purchase"))
    _create_enum("tally_purchase_status", ("pending", "partially_imported", "imported"))

    # inventory_source metadata — existing rows default to 'manual' (no behaviour change).
    op.add_column(
        "inventory_items",
        sa.Column(
            "inventory_source",
            inventory_source_enum,
            nullable=False,
            server_default="manual",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "tally_purchase_voucher",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tally_company_sync_id", sa.BigInteger(), nullable=False),
        sa.Column("tally_voucher_guid", sa.String(length=64), nullable=False),
        sa.Column("tally_master_id", sa.String(length=64), nullable=True),
        sa.Column("tally_voucher_number", sa.String(length=128), nullable=False),
        sa.Column("printed_invoice_number", sa.String(length=128), nullable=True),
        sa.Column("reference_number", sa.String(length=128), nullable=True),
        sa.Column("voucher_type", sa.String(length=64), nullable=True),
        sa.Column("voucher_date", sa.Date(), nullable=True),
        sa.Column("supplier_name", sa.String(length=256), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=True),
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("round_off", sa.Numeric(18, 2), nullable=True),
        sa.Column("cgst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("sgst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("igst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("cess_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("grand_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("raw_xml_gzip", postgresql.BYTEA(), nullable=True),
        sa.Column("status", tally_purchase_status_enum, server_default="pending", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
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
            ["tally_company_sync_id"],
            [f"{SCHEMA}.tally_company_sync.id"],
            name="fk_tally_purchase_voucher_company_sync",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_purchase_voucher"),
        sa.UniqueConstraint(
            "tally_company_sync_id",
            "tally_voucher_guid",
            name="uq_tally_purchase_voucher_company_guid",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_purchase_voucher_status",
        "tally_purchase_voucher",
        ["status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_purchase_voucher_voucher_date",
        "tally_purchase_voucher",
        ["voucher_date"],
        schema=SCHEMA,
    )

    op.create_table(
        "tally_purchase_line",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tally_purchase_voucher_id", sa.BigInteger(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("stock_item_name", sa.String(length=512), nullable=False),
        sa.Column("group_key", sa.String(length=512), nullable=False),
        sa.Column("quantity", sa.String(length=64), nullable=True),
        sa.Column("serials_json", sa.Text(), nullable=True),
        sa.Column("serial_source", sa.String(length=64), nullable=True),
        sa.Column("rate", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("taxable_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("cgst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("sgst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("igst_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("cess_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("imported", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("product_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
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
            ["tally_purchase_voucher_id"],
            [f"{SCHEMA}.tally_purchase_voucher.id"],
            name="fk_tally_purchase_line_voucher",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_purchase_line"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_purchase_line_voucher",
        "tally_purchase_line",
        ["tally_purchase_voucher_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_purchase_line_group_key",
        "tally_purchase_line",
        ["group_key"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tally_purchase_line_group_key", table_name="tally_purchase_line", schema=SCHEMA
    )
    op.drop_index("ix_tally_purchase_line_voucher", table_name="tally_purchase_line", schema=SCHEMA)
    op.drop_table("tally_purchase_line", schema=SCHEMA)

    op.drop_index(
        "ix_tally_purchase_voucher_voucher_date",
        table_name="tally_purchase_voucher",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_tally_purchase_voucher_status",
        table_name="tally_purchase_voucher",
        schema=SCHEMA,
    )
    op.drop_table("tally_purchase_voucher", schema=SCHEMA)

    op.drop_column("inventory_items", "inventory_source", schema=SCHEMA)

    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.tally_purchase_status"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.inventory_source"))
