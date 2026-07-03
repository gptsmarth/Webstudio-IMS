"""Enterprise release catalog — server-side release metadata (M13)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0037_enterprise_release_catalog"
down_revision: str | None = "0036_tally_probe_scheduler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

release_channel_enum = postgresql.ENUM(
    "development",
    "beta",
    "stable",
    name="release_channel",
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
    _create_enum("release_channel", ("development", "beta", "stable"))
    op.create_table(
        "software_releases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("release_version", sa.String(length=32), nullable=False),
        sa.Column("build_number", sa.Integer(), nullable=False),
        sa.Column("release_channel", release_channel_enum, nullable=False),
        sa.Column("git_commit", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("git_short", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("build_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("manifest", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("checksums", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "compatibility_matrix",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "supported_platforms",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_software_releases"),
        sa.UniqueConstraint(
            "release_version",
            "build_number",
            "release_channel",
            name="uq_software_releases_version_build_channel",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_software_releases_channel_published",
        "software_releases",
        ["release_channel", "published_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_software_releases_is_current",
        "software_releases",
        ["release_channel", "is_current"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_software_releases_is_current", table_name="software_releases", schema=SCHEMA)
    op.drop_index(
        "ix_software_releases_channel_published",
        table_name="software_releases",
        schema=SCHEMA,
    )
    op.drop_table("software_releases", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.release_channel"))
