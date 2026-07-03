"""Administration center: user archive, password age, integration API keys."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_admin_center"
down_revision: str | None = "0020_auth_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.users u
            SET password_changed_at = sub.latest_at
            FROM (
                SELECT user_id, MAX(created_at) AS latest_at
                FROM {SCHEMA}.password_history
                GROUP BY user_id
            ) sub
            WHERE u.id = sub.user_id AND u.password_changed_at IS NULL
            """),
    )
    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.users
            SET password_changed_at = created_at
            WHERE password_changed_at IS NULL AND password_hash IS NOT NULL
            """),
    )

    op.create_table(
        "integration_api_keys",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("service_type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("key_hint", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_user_id", sa.BigInteger(), nullable=True),
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
            ["created_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_integration_api_keys_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_integration_api_keys_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_api_keys_service_type",
        "integration_api_keys",
        ["service_type"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_api_keys_service_type", table_name="integration_api_keys", schema=SCHEMA
    )
    op.drop_table("integration_api_keys", schema=SCHEMA)
    op.drop_column("users", "password_changed_at", schema=SCHEMA)
    op.drop_column("users", "archived_at", schema=SCHEMA)
