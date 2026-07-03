"""Session metadata, login events, and password history for enterprise auth security."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_auth_security"
down_revision: str | None = "0019_model_prices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("device_label", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default="false"),
        schema=SCHEMA,
    )

    op.create_table(
        "password_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_password_history_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_password_history_user_created",
        "password_history",
        ["user_id", "created_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "login_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("device_label", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_login_events_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_login_events_created_at",
        "login_events",
        ["created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_login_events_username",
        "login_events",
        ["username"],
        schema=SCHEMA,
    )

    op.execute(
        sa.text(f"""
            INSERT INTO {SCHEMA}.system_settings (setting_key, setting_value, value_type, description)
            VALUES
                ('password_require_lowercase', 'true', 'boolean', 'Require lowercase letters in passwords'),
                ('password_history_count', '5', 'integer', 'Number of previous passwords to disallow reuse'),
                ('remember_me_ttl_days', '30', 'integer', 'Refresh token TTL when Remember Me is enabled')
            ON CONFLICT (setting_key) DO NOTHING
            """),
    )


def downgrade() -> None:
    op.drop_index("ix_login_events_username", table_name="login_events", schema=SCHEMA)
    op.drop_index("ix_login_events_created_at", table_name="login_events", schema=SCHEMA)
    op.drop_table("login_events", schema=SCHEMA)
    op.drop_index("ix_password_history_user_created", table_name="password_history", schema=SCHEMA)
    op.drop_table("password_history", schema=SCHEMA)
    op.drop_column("refresh_tokens", "remember_me", schema=SCHEMA)
    op.drop_column("refresh_tokens", "last_used_at", schema=SCHEMA)
    op.drop_column("refresh_tokens", "device_label", schema=SCHEMA)
    op.drop_column("refresh_tokens", "user_agent", schema=SCHEMA)
    op.drop_column("refresh_tokens", "ip_address", schema=SCHEMA)
