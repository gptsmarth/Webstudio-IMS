"""Create users, refresh_tokens, system_settings; link audit_logs.actor_user_id."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_users_authentication"
down_revision: str | None = "0007_audit_log_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


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
    _create_enum("user_role", ("main_admin", "admin", "salesperson", "service_account"))
    _create_enum("user_status", ("active", "disabled"))
    _create_enum("theme_preference", ("light", "dark", "system"))
    _create_enum("setting_value_type", ("string", "integer", "boolean", "json", "cron"))

    user_role_enum = postgresql.ENUM(
        "main_admin",
        "admin",
        "salesperson",
        "service_account",
        name="user_role",
        schema=SCHEMA,
        create_type=False,
    )
    user_status_enum = postgresql.ENUM(
        "active",
        "disabled",
        name="user_status",
        schema=SCHEMA,
        create_type=False,
    )
    theme_preference_enum = postgresql.ENUM(
        "light",
        "dark",
        "system",
        name="theme_preference",
        schema=SCHEMA,
        create_type=False,
    )
    setting_value_type_enum = postgresql.ENUM(
        "string",
        "integer",
        "boolean",
        "json",
        "cron",
        name="setting_value_type",
        schema=SCHEMA,
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("status", user_status_enum, nullable=False, server_default="active"),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("theme_preference", theme_preference_enum, nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_users_created_by_user",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_users_updated_by_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_username", "users", ["username"], schema=SCHEMA)
    op.create_index("ix_users_role", "users", ["role"], schema=SCHEMA)
    op.create_index("ix_users_status", "users", ["status"], schema=SCHEMA)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_refresh_tokens_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            [f"{SCHEMA}.refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        schema=SCHEMA,
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema=SCHEMA)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], schema=SCHEMA)

    op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("setting_key", sa.String(length=128), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("value_type", setting_value_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_system_settings_updated_by_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_system_settings"),
        sa.UniqueConstraint("setting_key", name="uq_system_settings_key"),
        schema=SCHEMA,
    )

    op.execute(
        sa.text(f"""
            INSERT INTO {SCHEMA}.system_settings
                (setting_key, setting_value, value_type, description)
            VALUES
                ('system_initialized', 'false', 'boolean',
                 'Authoritative first-time setup flag'),
                ('lockout_threshold', '5', 'integer',
                 'Failed login attempts before lockout'),
                ('lockout_duration_minutes', '15', 'integer',
                 'Account lockout duration in minutes')
            """),
    )

    op.create_foreign_key(
        "fk_audit_logs_actor_user",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_logs_actor_user", "audit_logs", schema=SCHEMA, type_="foreignkey")
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.system_settings CASCADE"))
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.refresh_tokens CASCADE"))
    op.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.users CASCADE"))
    for enum_name in ("setting_value_type", "theme_preference", "user_status", "user_role"):
        op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.{enum_name}"))
