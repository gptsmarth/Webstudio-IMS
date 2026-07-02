"""Rename catalogue archive permissions to delete for enterprise delete management."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_catalogue_delete_perm"
down_revision: str | None = "0030_brand_hard_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

_PERMISSION_RENAMES: tuple[tuple[str, str], ...] = (
    ("brands:archive", "brands:delete"),
    ("product_models:archive", "product_models:delete"),
    ("locations:archive", "locations:delete"),
)


def upgrade() -> None:
    for old_permission, new_permission in _PERMISSION_RENAMES:
        op.execute(
            sa.text(f"""
                UPDATE {SCHEMA}.custom_access_role_permissions AS cap
                SET permission = :new_permission
                WHERE cap.permission = :old_permission
                  AND NOT EXISTS (
                      SELECT 1
                      FROM {SCHEMA}.custom_access_role_permissions AS existing
                      WHERE existing.role_id = cap.role_id
                        AND existing.permission = :new_permission
                  )
            """).bindparams(old_permission=old_permission, new_permission=new_permission),
        )
        op.execute(
            sa.text(f"""
                DELETE FROM {SCHEMA}.custom_access_role_permissions
                WHERE permission = :old_permission
            """).bindparams(old_permission=old_permission),
        )


def downgrade() -> None:
    for old_permission, new_permission in _PERMISSION_RENAMES:
        op.execute(
            sa.text(f"""
                UPDATE {SCHEMA}.custom_access_role_permissions AS cap
                SET permission = :old_permission
                WHERE cap.permission = :new_permission
                  AND NOT EXISTS (
                      SELECT 1
                      FROM {SCHEMA}.custom_access_role_permissions AS existing
                      WHERE existing.role_id = cap.role_id
                        AND existing.permission = :old_permission
                  )
            """).bindparams(old_permission=old_permission, new_permission=new_permission),
        )
        op.execute(
            sa.text(f"""
                DELETE FROM {SCHEMA}.custom_access_role_permissions
                WHERE permission = :new_permission
            """).bindparams(new_permission=new_permission),
        )
