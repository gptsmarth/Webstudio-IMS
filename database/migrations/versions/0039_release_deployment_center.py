"""Release deployment events and administrator approval audit trail (M13C)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0039_release_deployment_center"
down_revision: str | None = "0038_github_release_sync"
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
        "release_deployment_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("release_version", sa.String(length=32), nullable=True),
        sa.Column("build_number", sa.Integer(), nullable=True),
        sa.Column("release_channel", release_channel_enum, nullable=True),
        sa.Column("job_id", sa.BigInteger(), nullable=True),
        sa.Column("release_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "administrator_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("performed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("detail_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_release_deployment_events"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_release_deployment_events_created",
        "release_deployment_events",
        ["created_at"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_deployment_events_created",
        table_name="release_deployment_events",
        schema=SCHEMA,
    )
    op.drop_table("release_deployment_events", schema=SCHEMA)
