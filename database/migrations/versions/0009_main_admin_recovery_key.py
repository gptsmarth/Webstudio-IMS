"""Add Main Admin recovery key columns to users."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_main_admin_recovery_key"
down_revision: str | None = "0008_users_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("recovery_key_hash", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column("recovery_key_created_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column("recovery_key_last_used_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("users", "recovery_key_last_used_at", schema=SCHEMA)
    op.drop_column("users", "recovery_key_created_at", schema=SCHEMA)
    op.drop_column("users", "recovery_key_hash", schema=SCHEMA)
