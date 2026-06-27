"""Create brand and location reference tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_reference_data"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

location_type_enum = postgresql.ENUM(
    "retail_floor",
    "warehouse",
    "other",
    name="location_type",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA}.location_type AS ENUM (
                    'retail_floor', 'warehouse', 'other'
                );
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """))

    op.create_table(
        "brands",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_brands"),
        sa.UniqueConstraint("name", name="uq_brands_name"),
        schema=SCHEMA,
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("location_type", location_type_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.BigInteger(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
        sa.UniqueConstraint("name", name="uq_locations_name"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.locations CASCADE"))
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.brands CASCADE"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.location_type"))
