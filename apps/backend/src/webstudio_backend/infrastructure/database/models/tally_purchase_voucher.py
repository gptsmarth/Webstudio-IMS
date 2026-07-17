"""Purchase Import Queue voucher header.

Additive Purchase Import feature (Day Book Purchase vouchers projected into a
review queue). This NEVER changes inventory — inventory is only created after
explicit, per-model-group user approval via the Purchase Import API.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    TALLY_PURCHASE_STATUS_ENUM_NAME,
    TallyPurchaseStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class TallyPurchaseVoucher(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tally_purchase_voucher"
    __table_args__ = (
        UniqueConstraint(
            "tally_company_sync_id",
            "tally_voucher_guid",
            name="uq_tally_purchase_voucher_company_guid",
        ),
        {"schema": DATABASE_SCHEMA},
    )

    tally_company_sync_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_company_sync.id",
            name="fk_tally_purchase_voucher_company_sync",
        ),
        nullable=False,
    )
    tally_voucher_guid: Mapped[str] = mapped_column(String(64), nullable=False)
    tally_master_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_voucher_number: Mapped[str] = mapped_column(String(128), nullable=False)
    printed_invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voucher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voucher_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    round_off: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cgst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    sgst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    igst_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cess_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    grand_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_xml_gzip: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[TallyPurchaseStatus] = mapped_column(
        Enum(
            TallyPurchaseStatus,
            name=TALLY_PURCHASE_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=TallyPurchaseStatus.PENDING,
        server_default=TallyPurchaseStatus.PENDING.value,
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lines: Mapped[list[TallyPurchaseLine]] = relationship(
        "TallyPurchaseLine",
        back_populates="voucher",
        cascade="all, delete-orphan",
        order_by="TallyPurchaseLine.line_index",
    )


# Imported at the bottom to avoid a circular import at module load time.
from webstudio_backend.infrastructure.database.models.tally_purchase_line import (  # noqa: E402
    TallyPurchaseLine,
)
