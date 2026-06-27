"""Create product_models table."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_product_model"
down_revision: str | None = "0002_reference_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

product_model_status_enum = postgresql.ENUM(
    "active",
    "archived",
    name="product_model_status",
    schema=SCHEMA,
    create_type=False,
)
storage_unit_enum = postgresql.ENUM(
    "GB",
    "TB",
    name="storage_unit",
    schema=SCHEMA,
    create_type=False,
)
storage_type_enum = postgresql.ENUM(
    "SSD",
    "HDD",
    name="storage_type",
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
    _create_enum("product_model_status", ("active", "archived"))
    _create_enum("storage_unit", ("GB", "TB"))
    _create_enum("storage_type", ("SSD", "HDD"))

    op.create_table(
        "product_models",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("brand_id", sa.BigInteger(), nullable=False),
        sa.Column("model_number", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("cpu", sa.String(length=128), nullable=False),
        sa.Column("gpu", sa.String(length=128), nullable=True),
        sa.Column("ram_gb", sa.Integer(), nullable=False),
        sa.Column("storage_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("storage_unit", storage_unit_enum, nullable=False),
        sa.Column("storage_type", storage_type_enum, nullable=False),
        sa.Column(
            "status",
            product_model_status_enum,
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
            ["brand_id"],
            [f"{SCHEMA}.brands.id"],
            name="fk_product_models_brand",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_models"),
        sa.UniqueConstraint(
            "brand_id",
            "model_number",
            name="uq_product_models_brand_model_number",
        ),
        schema=SCHEMA,
    )

    op.create_index("ix_product_models_brand_id", "product_models", ["brand_id"], schema=SCHEMA)
    op.create_index("ix_product_models_status", "product_models", ["status"], schema=SCHEMA)
    op.create_index(
        "ix_product_models_model_number",
        "product_models",
        ["model_number"],
        schema=SCHEMA,
    )
    op.create_index("ix_product_models_model_name", "product_models", ["model_name"], schema=SCHEMA)


def downgrade() -> None:
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.product_models CASCADE"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.product_model_status"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.storage_unit"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.storage_type"))
