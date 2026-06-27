"""Create inventory_items table."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_inventory_item"
down_revision: str | None = "0003_product_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

inventory_status_enum = postgresql.ENUM(
    "received",
    "available",
    "reserved",
    "sold",
    name="inventory_status",
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
    _create_enum("inventory_status", ("received", "available", "reserved", "sold"))

    op.create_table(
        "inventory_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("serial_number", sa.String(length=128), nullable=False),
        sa.Column("product_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=False),
        sa.Column("current_location_id", sa.BigInteger(), nullable=False),
        sa.Column("status", inventory_status_enum, nullable=False),
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
            ["product_model_id"],
            [f"{SCHEMA}.product_models.id"],
            name="fk_inventory_items_product_model",
        ),
        sa.ForeignKeyConstraint(
            ["current_location_id"],
            [f"{SCHEMA}.locations.id"],
            name="fk_inventory_items_current_location",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint("serial_number", name="uq_inventory_items_serial_number"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_inventory_items_product_model_id",
        "inventory_items",
        ["product_model_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_current_location_id",
        "inventory_items",
        ["current_location_id"],
        schema=SCHEMA,
    )
    op.create_index("ix_inventory_items_status", "inventory_items", ["status"], schema=SCHEMA)
    op.create_index("ix_inventory_items_color", "inventory_items", ["color"], schema=SCHEMA)


def downgrade() -> None:
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.inventory_items CASCADE"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.inventory_status"))
