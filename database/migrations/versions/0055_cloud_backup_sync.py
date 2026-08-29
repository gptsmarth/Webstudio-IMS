"""Google Drive cloud backup sync: connection storage + per-backup upload tracking.

Revision ID: 0055_cloud_backup_sync
Revises: 0054_purge_archived_serials

Purely additive:
  * new `cloud_backup_connections` table holding the encrypted Drive refresh
    token and connection/sync status (see docs/architecture/future/cloud-backup-sync.md).
  * three nullable columns on `backup_runs` tracking whether/when each backup
    was uploaded to Drive. Existing rows and queries are unaffected.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0055_cloud_backup_sync"
down_revision: str | None = "0054_purge_archived_serials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        sa.text(f"""
            DO $$ BEGIN
                ALTER TYPE {SCHEMA}.{enum_name} ADD VALUE IF NOT EXISTS '{value}';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """),
    )


def upgrade() -> None:
    for value in (
        "cloud_sync_completed",
        "cloud_sync_failed",
        "cloud_reconnect_needed",
    ):
        _add_enum_value("notification_type", value)

    op.create_table(
        "cloud_backup_connections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("account_email", sa.String(length=256), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("drive_folder_id", sa.String(length=128), nullable=True),
        sa.Column("retention_count", sa.BigInteger(), nullable=False, server_default="25"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="connected"),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            ["connected_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_cloud_backup_connections_connected_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cloud_backup_connections"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cloud_backup_connections_provider",
        "cloud_backup_connections",
        ["provider"],
        unique=False,
        schema=SCHEMA,
    )

    op.add_column(
        "backup_runs",
        sa.Column("cloud_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "backup_runs",
        sa.Column("cloud_upload_status", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "backup_runs",
        sa.Column("cloud_file_id", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("backup_runs", "cloud_file_id", schema=SCHEMA)
    op.drop_column("backup_runs", "cloud_upload_status", schema=SCHEMA)
    op.drop_column("backup_runs", "cloud_uploaded_at", schema=SCHEMA)

    op.drop_index(
        "ix_cloud_backup_connections_provider",
        table_name="cloud_backup_connections",
        schema=SCHEMA,
    )
    op.drop_table("cloud_backup_connections", schema=SCHEMA)
