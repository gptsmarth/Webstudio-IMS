"""GitHub release sync — download queue, artifacts, and scheduler seed (M13B)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0038_github_release_sync"
down_revision: str | None = "0037_enterprise_release_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

release_download_status_enum = postgresql.ENUM(
    "pending",
    "queued",
    "downloading",
    "verifying",
    "completed",
    "failed",
    "skipped",
    name="release_download_status",
    schema=SCHEMA,
    create_type=False,
)

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
    _create_enum(
        "release_download_status",
        ("pending", "queued", "downloading", "verifying", "completed", "failed", "skipped"),
    )
    op.create_table(
        "release_download_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("github_release_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_name", sa.String(length=64), nullable=False),
        sa.Column("release_version", sa.String(length=32), nullable=False),
        sa.Column("build_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("release_channel", release_channel_enum, nullable=False),
        sa.Column(
            "status",
            release_download_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("bundle_dir", sa.Text(), nullable=True),
        sa.Column("github_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("manifest_validated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("checksums_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_release_download_jobs"),
        sa.UniqueConstraint(
            "github_release_id",
            "release_channel",
            name="uq_release_download_jobs_github_channel",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_release_download_jobs_status_retry",
        "release_download_jobs",
        ["status", "next_retry_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_table(
        "release_download_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("artifact_name", sa.String(length=256), nullable=False),
        sa.Column("github_asset_id", sa.BigInteger(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("expected_sha256", sa.String(length=64), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("partial_path", sa.Text(), nullable=True),
        sa.Column("bytes_downloaded", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            release_download_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA}.release_download_jobs.id"],
            name="fk_release_download_artifacts_job_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_release_download_artifacts"),
        sa.UniqueConstraint(
            "job_id",
            "artifact_name",
            name="uq_release_download_artifacts_job_artifact",
        ),
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.scheduler_runtime_state (scheduler_key, interval_seconds)
            VALUES ('github_release_sync', 900)
            ON CONFLICT (scheduler_key) DO NOTHING
            """,
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.scheduler_runtime_state WHERE scheduler_key = 'github_release_sync'",
        ),
    )
    op.drop_table("release_download_artifacts", schema=SCHEMA)
    op.drop_index("ix_release_download_jobs_status_retry", table_name="release_download_jobs", schema=SCHEMA)
    op.drop_table("release_download_jobs", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.release_download_status"))
