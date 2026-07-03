"""Enterprise backup engine — backup run history and verification."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_backup_engine"
down_revision: str | None = "0021_admin_center"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_table(
        "backup_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("archive_path", sa.Text(), nullable=False),
        sa.Column("backup_type", sa.String(length=32), nullable=False, server_default="full"),
        sa.Column("trigger_type", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("storage_backend", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column(
            "verification_status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("creator_user_id", sa.BigInteger(), nullable=True),
        sa.Column("creator_display_name", sa.String(length=128), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("errors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("manifest_json", sa.Text(), nullable=True),
        sa.Column("base_backup_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["creator_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_backup_runs_creator_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["base_backup_id"],
            [f"{SCHEMA}.backup_runs.id"],
            name="fk_backup_runs_base_backup",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backup_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_backup_runs_created_at",
        "backup_runs",
        ["created_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_backup_runs_status",
        "backup_runs",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_backup_runs_status", table_name="backup_runs", schema=SCHEMA)
    op.drop_index("ix_backup_runs_created_at", table_name="backup_runs", schema=SCHEMA)
    op.drop_table("backup_runs", schema=SCHEMA)
