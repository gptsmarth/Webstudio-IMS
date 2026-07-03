"""Enterprise rollback run tracking (M13F)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0041_enterprise_rollback"
down_revision: str | None = "0040_deployment_engine"
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
        "enterprise_rollback_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("release_channel", release_channel_enum, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("current_step", sa.String(length=64), nullable=True),
        sa.Column("steps_json", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("from_release_version", sa.String(length=32), nullable=False),
        sa.Column("from_build_number", sa.Integer(), nullable=False),
        sa.Column("from_release_id", sa.BigInteger(), nullable=True),
        sa.Column("to_release_version", sa.String(length=32), nullable=False),
        sa.Column("to_build_number", sa.Integer(), nullable=False),
        sa.Column("to_release_id", sa.BigInteger(), nullable=True),
        sa.Column("deployment_run_id", sa.BigInteger(), nullable=True),
        sa.Column("deployment_event_id", sa.BigInteger(), nullable=True),
        sa.Column("pre_rollback_backup_filename", sa.String(length=256), nullable=True),
        sa.Column("database_restore_filename", sa.String(length=256), nullable=True),
        sa.Column("scheduler_snapshot", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("config_snapshot_path", sa.Text(), nullable=True),
        sa.Column("service_config_snapshot_path", sa.Text(), nullable=True),
        sa.Column("target_bundle_dir", sa.Text(), nullable=True),
        sa.Column("health_status", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("performed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_enterprise_rollback_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enterprise_rollback_runs_created",
        "enterprise_rollback_runs",
        ["created_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enterprise_rollback_runs_status",
        "enterprise_rollback_runs",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_enterprise_rollback_runs_status", table_name="enterprise_rollback_runs", schema=SCHEMA)
    op.drop_index("ix_enterprise_rollback_runs_created", table_name="enterprise_rollback_runs", schema=SCHEMA)
    op.drop_table("enterprise_rollback_runs", schema=SCHEMA)
