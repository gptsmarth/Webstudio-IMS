"""Tally processed invoice state."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    TALLY_PROCESSING_STATUS_ENUM_NAME,
    TallyProcessingStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class TallyProcessedInvoice(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tally_processed_invoice"

    tally_company_sync_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.tally_company_sync.id", name="fk_tally_processed_invoice_company_sync"),
        nullable=False,
    )
    tally_voucher_guid: Mapped[str] = mapped_column(String(64), nullable=False)
    tally_master_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_voucher_number: Mapped[str] = mapped_column(String(128), nullable=False)
    printed_invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voucher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voucher_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    party_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    voucher_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    processing_status: Mapped[TallyProcessingStatus] = mapped_column(
        Enum(
            TallyProcessingStatus,
            name=TALLY_PROCESSING_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    first_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
