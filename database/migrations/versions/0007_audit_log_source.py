"""Add audit source column for distinguishing automated event origins."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_audit_log_source"
down_revision: str | None = "0006_audit_log_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

audit_source_enum = postgresql.ENUM(
    "MANUAL",
    "TALLY_SYNC",
    "BACKGROUND_JOB",
    "SYSTEM",
    name="audit_source",
    schema=SCHEMA,
    create_type=False,
)


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
    _create_enum(
        "audit_source",
        ("MANUAL", "TALLY_SYNC", "BACKGROUND_JOB", "SYSTEM"),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "source",
            audit_source_enum,
            nullable=False,
            server_default="MANUAL",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_source",
        "audit_logs",
        ["source"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_source", table_name="audit_logs", schema=SCHEMA)
    op.drop_column("audit_logs", "source", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.audit_source"))
