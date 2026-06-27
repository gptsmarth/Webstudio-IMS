"""Create inventory_movements table."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_inventory_movement"
down_revision: str | None = "0004_inventory_item"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

movement_reason_enum = postgresql.ENUM(
    "new_stock",
    "store_transfer",
    "display",
    "sale_preparation",
    "correction",
    "other",
    name="movement_reason",
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
        "movement_reason",
        (
            "new_stock",
            "store_transfer",
            "display",
            "sale_preparation",
            "correction",
            "other",
        ),
    )

    op.create_table(
        "inventory_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_location_id", sa.BigInteger(), nullable=False),
        sa.Column("to_location_id", sa.BigInteger(), nullable=False),
        sa.Column("movement_reason", movement_reason_enum, nullable=False),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "from_location_id <> to_location_id",
            name="ck_inv_movements_diff_locs",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            [f"{SCHEMA}.inventory_items.id"],
            name="fk_inventory_movements_inventory_item",
        ),
        sa.ForeignKeyConstraint(
            ["from_location_id"],
            [f"{SCHEMA}.locations.id"],
            name="fk_inventory_movements_from_location",
        ),
        sa.ForeignKeyConstraint(
            ["to_location_id"],
            [f"{SCHEMA}.locations.id"],
            name="fk_inventory_movements_to_location",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_movements"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_inventory_movements_inventory_item_id",
        "inventory_movements",
        ["inventory_item_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_from_location_id",
        "inventory_movements",
        ["from_location_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_to_location_id",
        "inventory_movements",
        ["to_location_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_moved_at",
        "inventory_movements",
        ["moved_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_movement_reason",
        "inventory_movements",
        ["movement_reason"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.inventory_movements CASCADE"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.movement_reason"))
