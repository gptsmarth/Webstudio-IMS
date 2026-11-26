"""Persist ASUS activation schemes and settlements."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059_asus_activation"
down_revision: str | None = "0058_laptop_comparison_cache"
branch_labels = None
depends_on = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_table(
        "asus_activation_schemes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("date_from", sa.Date(), nullable=False, index=True),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("rules", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("date_from <= date_to", name="ck_asus_activation_date_range"),
        schema=SCHEMA,
    )
    op.create_table(
        "asus_activation_workbooks",
        sa.Column(
            "scheme_id",
            sa.Uuid(),
            sa.ForeignKey(f"{SCHEMA}.asus_activation_schemes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        schema=SCHEMA,
    )
    op.create_table(
        "asus_activation_receipts",
        sa.Column(
            "sale_id",
            sa.BigInteger(),
            sa.ForeignKey(f"{SCHEMA}.sales.id"),
            primary_key=True,
            autoincrement=False,
        ),
        sa.Column(
            "scheme_id",
            sa.Uuid(),
            sa.ForeignKey(f"{SCHEMA}.asus_activation_schemes.id"),
            nullable=False,
        ),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("digest", sa.String(64), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("receipt_scheme", sa.String(500), nullable=True),
        sa.Column("application_no", sa.String(128), nullable=True),
        sa.Column("record_note", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "amount >= 0 AND expected_amount > 0", name="ck_asus_activation_receipt_amounts"
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "asus_activation_receipts",
        "asus_activation_workbooks",
        "asus_activation_schemes",
    ):
        op.drop_table(table, schema=SCHEMA)
