"""Add product category (laptop/accessory), accessory kind, and part number."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045_product_accessory_category"
down_revision: str | None = "0044_sale_amount_excluding_gst"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA}.{enum_name} AS ENUM ({quoted_values});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """))


def upgrade() -> None:
    _create_enum("product_category", ("laptop", "accessory"))
    _create_enum(
        "accessory_kind",
        (
            "mouse",
            "keyboard",
            "charger",
            "headset",
            "bag",
            "dock",
            "cable",
            "adapter",
            "storage",
            "other",
        ),
    )

    product_category_enum = postgresql.ENUM(
        "laptop",
        "accessory",
        name="product_category",
        schema=SCHEMA,
        create_type=False,
    )
    accessory_kind_enum = postgresql.ENUM(
        "mouse",
        "keyboard",
        "charger",
        "headset",
        "bag",
        "dock",
        "cable",
        "adapter",
        "storage",
        "other",
        name="accessory_kind",
        schema=SCHEMA,
        create_type=False,
    )

    op.add_column(
        "product_models",
        sa.Column(
            "category",
            product_category_enum,
            nullable=False,
            server_default="laptop",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("accessory_kind", accessory_kind_enum, nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("part_number", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )

    op.alter_column("product_models", "cpu", nullable=True, schema=SCHEMA)
    op.alter_column("product_models", "ram_gb", nullable=True, schema=SCHEMA)
    op.alter_column("product_models", "storage_value", nullable=True, schema=SCHEMA)
    op.alter_column("product_models", "storage_unit", nullable=True, schema=SCHEMA)
    op.alter_column("product_models", "storage_type", nullable=True, schema=SCHEMA)

    op.create_index(
        "ix_product_models_category",
        "product_models",
        ["category"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_product_models_part_number",
        "product_models",
        ["part_number"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(sa.text(f"""
            UPDATE {SCHEMA}.product_models
            SET cpu = COALESCE(cpu, 'Unknown'),
                ram_gb = COALESCE(ram_gb, 1),
                storage_value = COALESCE(storage_value, 1),
                storage_unit = COALESCE(storage_unit, 'GB'),
                storage_type = COALESCE(storage_type, 'SSD')
            WHERE category = 'accessory'
            """))

    op.drop_index("ix_product_models_part_number", table_name="product_models", schema=SCHEMA)
    op.drop_index("ix_product_models_category", table_name="product_models", schema=SCHEMA)

    op.alter_column("product_models", "storage_type", nullable=False, schema=SCHEMA)
    op.alter_column("product_models", "storage_unit", nullable=False, schema=SCHEMA)
    op.alter_column("product_models", "storage_value", nullable=False, schema=SCHEMA)
    op.alter_column("product_models", "ram_gb", nullable=False, schema=SCHEMA)
    op.alter_column("product_models", "cpu", nullable=False, schema=SCHEMA)

    op.drop_column("product_models", "part_number", schema=SCHEMA)
    op.drop_column("product_models", "accessory_kind", schema=SCHEMA)
    op.drop_column("product_models", "category", schema=SCHEMA)

    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.accessory_kind"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.product_category"))
