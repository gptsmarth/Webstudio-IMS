"""Editable ASUS activation periods and expected CN corrections."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060_asus_activation_edits"
down_revision: str | None = "0059_asus_activation"
branch_labels = None
depends_on = None

SCHEMA = "webstudio"
SCHEMES = "asus_activation_schemes"
RECEIPTS = "asus_activation_receipts"
OVERRIDES = "asus_activation_cn_overrides"


def upgrade() -> None:
    op.add_column(
        SCHEMES,
        sa.Column("revision", sa.Integer, server_default="0", nullable=False),
        schema=SCHEMA,
    )
    for name, default in (("rate_overrides", "{}"), ("history", "[]")):
        op.add_column(
            SCHEMES,
            sa.Column(
                name,
                postgresql.JSONB,
                server_default=sa.text(f"'{default}'::jsonb"),
                nullable=False,
            ),
            schema=SCHEMA,
        )
    op.add_column(RECEIPTS, sa.Column("scheme_snapshot", postgresql.JSONB), schema=SCHEMA)
    op.add_column(RECEIPTS, sa.Column("resolved_expected_amount", sa.Numeric(12, 2)), schema=SCHEMA)
    op.execute(
        "UPDATE webstudio.asus_activation_receipts SET resolved_expected_amount = expected_amount "
        "WHERE resolved_at IS NOT NULL"
    )
    op.drop_constraint("ck_asus_activation_receipt_amounts", RECEIPTS, type_="check", schema=SCHEMA)
    op.create_check_constraint(
        "ck_asus_activation_receipt_amounts",
        RECEIPTS,
        "amount >= 0 AND expected_amount >= 0",
        schema=SCHEMA,
    )
    op.create_table(
        OVERRIDES,
        sa.Column(
            "sale_id",
            sa.BigInteger,
            sa.ForeignKey(f"{SCHEMA}.sales.id"),
            primary_key=True,
            autoincrement=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("updated_by", sa.BigInteger, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_activation_cn_override_amount"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table(OVERRIDES, schema=SCHEMA)
    op.drop_constraint("ck_asus_activation_receipt_amounts", RECEIPTS, type_="check", schema=SCHEMA)
    op.create_check_constraint(
        "ck_asus_activation_receipt_amounts",
        RECEIPTS,
        "amount >= 0 AND expected_amount > 0",
        schema=SCHEMA,
    )
    op.drop_column(RECEIPTS, "resolved_expected_amount", schema=SCHEMA)
    op.drop_column(RECEIPTS, "scheme_snapshot", schema=SCHEMA)
    for name in ("history", "rate_overrides", "revision"):
        op.drop_column(SCHEMES, name, schema=SCHEMA)
