"""Enterprise deployment run tracking (M13D)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0040_deployment_engine"
down_revision: str | None = "0039_release_deployment_center"
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


def upgrade() -> None:
    op.create_table(
        "release_deployment_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=True),
        sa.Column("release_version", sa.String(length=32), nullable=False),
        sa.Column("build_number", sa.Integer(), nullable=False),
        sa.Column("release_channel", release_channel_enum, nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("current_step", sa.String(length=64), nullable=True),
        sa.Column("steps_json", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pre_backup_run_id", sa.BigInteger(), nullable=True),
        sa.Column("pre_backup_filename", sa.String(length=256), nullable=True),
        sa.Column("rollback_backup_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "scheduler_snapshot", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("config_snapshot_path", sa.Text(), nullable=True),
        sa.Column("service_config_snapshot_path", sa.Text(), nullable=True),
        sa.Column("previous_release_id", sa.BigInteger(), nullable=True),
        sa.Column("bundle_dir", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("performed_by_user_id", sa.BigInteger(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_release_deployment_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_release_deployment_runs_created",
        "release_deployment_runs",
        ["created_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_release_deployment_runs_status",
        "release_deployment_runs",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_deployment_runs_status", table_name="release_deployment_runs", schema=SCHEMA
    )
    op.drop_index(
        "ix_release_deployment_runs_created", table_name="release_deployment_runs", schema=SCHEMA
    )
    op.drop_table("release_deployment_runs", schema=SCHEMA)
