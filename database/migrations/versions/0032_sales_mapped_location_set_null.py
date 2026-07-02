"""Allow location delete while preserving Tally sales via snapshot_location_name."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_sales_mapped_loc_null"
down_revision: str | None = "0031_catalogue_delete_perm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.sales AS sale
            SET snapshot_location_name = location.name
            FROM {SCHEMA}.locations AS location
            WHERE sale.mapped_location_id = location.id
              AND sale.snapshot_location_name IS NULL
            """),
    )

    op.drop_constraint("fk_sales_mapped_location", "sales", schema=SCHEMA, type_="foreignkey")
    op.create_foreign_key(
        "fk_sales_mapped_location",
        "sales",
        "locations",
        ["mapped_location_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sales_mapped_location", "sales", schema=SCHEMA, type_="foreignkey")
    op.create_foreign_key(
        "fk_sales_mapped_location",
        "sales",
        "locations",
        ["mapped_location_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
