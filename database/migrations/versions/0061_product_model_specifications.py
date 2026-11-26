"""Store durable supplemental laptop specifications with the product model."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0061_product_model_specs"
down_revision: str | None = "0060_asus_activation_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_models",
        sa.Column(
            "detailed_specifications", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        schema="webstudio",
    )
    for name in ("specifications_researched_at", "specifications_retry_at"):
        op.add_column(
            "product_models", sa.Column(name, sa.DateTime(timezone=True)), schema="webstudio"
        )


def downgrade() -> None:
    for name in (
        "specifications_retry_at",
        "specifications_researched_at",
        "detailed_specifications",
    ):
        op.drop_column("product_models", name, schema="webstudio")
