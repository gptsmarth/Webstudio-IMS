"""Client version observations for deployment analytics (M13I)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_deployment_monitoring"
down_revision: str | None = "0041_enterprise_rollback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_table(
        "client_version_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("client_version", sa.String(length=32), nullable=False),
        sa.Column("release_channel", sa.String(length=16), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_client_version_observations"),
        sa.UniqueConstraint(
            "platform",
            "client_version",
            name="uq_client_version_observations_platform_version",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_client_version_observations_platform",
        "client_version_observations",
        ["platform"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_client_version_observations_last_seen_at",
        "client_version_observations",
        ["last_seen_at"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_client_version_observations_last_seen_at",
        table_name="client_version_observations",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_client_version_observations_platform",
        table_name="client_version_observations",
        schema=SCHEMA,
    )
    op.drop_table("client_version_observations", schema=SCHEMA)
