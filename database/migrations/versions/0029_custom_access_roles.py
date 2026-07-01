"""Custom access roles with granular permission sets."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_custom_roles"
down_revision: str | None = "0028_sale_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_table(
        "custom_access_roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_custom_access_roles_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_custom_access_roles_updated_by",
        ),
        sa.UniqueConstraint("name", name="uq_custom_access_roles_name"),
        schema=SCHEMA,
    )
    op.create_table(
        "custom_access_role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.custom_access_roles.id"],
            name="fk_custom_access_role_permissions_role",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission", name="pk_custom_access_role_permissions"),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column("custom_access_role_id", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_users_custom_access_role",
        "users",
        "custom_access_roles",
        ["custom_access_role_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_custom_access_role", "users", schema=SCHEMA, type_="foreignkey")
    op.drop_column("users", "custom_access_role_id", schema=SCHEMA)
    op.drop_table("custom_access_role_permissions", schema=SCHEMA)
    op.drop_table("custom_access_roles", schema=SCHEMA)
