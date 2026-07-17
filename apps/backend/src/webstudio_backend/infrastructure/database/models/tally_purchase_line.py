"""Purchase Import Queue line (one row per Tally inventory entry).

Lines are grouped by ``stock_item_name`` at the API layer to form model groups.
Import happens per model group; on import each line in the group records the
resolved ``product_model_id`` and is flagged ``imported``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class TallyPurchaseLine(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tally_purchase_line"
    __table_args__ = ({"schema": DATABASE_SCHEMA},)

    tally_purchase_voucher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_purchase_voucher.id",
            name="fk_tally_purchase_line_voucher",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_item_name: Mapped[str] = mapped_column(String(512), nullable=False)
    group_key: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serials_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    serial_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    taxable_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cgst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    sgst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    igst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cess_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    imported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    product_model_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    voucher: Mapped[TallyPurchaseVoucher] = relationship(  # noqa: F821
        "TallyPurchaseVoucher",
        back_populates="lines",
    )
