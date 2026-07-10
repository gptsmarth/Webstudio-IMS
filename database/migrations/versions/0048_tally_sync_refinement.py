"""P0 final refinement: unmatched serialized items + sale serial_source.

Revision ID: 0048_tally_sync_refinement
Revises: 0047_tally_sync_redesign
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048_tally_sync_refinement"
down_revision: str | None = "0047_tally_sync_redesign"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        sa.text(
            f"ALTER TYPE {SCHEMA}.{enum_name} ADD VALUE IF NOT EXISTS '{value}'",
        ),
    )


def upgrade() -> None:
    _add_enum_value("tally_line_outcome", "unmatched_serialized_item")

    op.add_column(
        "tally_processed_invoice_line",
        sa.Column(
            "is_unmatched_serialized",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("serial_source", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_line_unmatched",
        "tally_processed_invoice_line",
        ["is_unmatched_serialized"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tally_processed_invoice_line_unmatched",
        table_name="tally_processed_invoice_line",
        schema=SCHEMA,
    )
    op.drop_column("sales", "serial_source", schema=SCHEMA)
    op.drop_column("tally_processed_invoice_line", "is_unmatched_serialized", schema=SCHEMA)
