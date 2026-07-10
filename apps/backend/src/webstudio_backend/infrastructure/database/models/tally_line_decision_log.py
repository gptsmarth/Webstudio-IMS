"""Immutable Tally line decision log for auditability."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class TallyLineDecisionLog(Base, PrimaryKeyMixin):
    __tablename__ = "tally_line_decision_log"

    tally_processed_invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_processed_invoice.id",
            name="fk_tally_line_decision_log_invoice",
        ),
        nullable=False,
    )
    tally_processed_invoice_line_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tally_voucher_guid: Mapped[str] = mapped_column(String(64), nullable=False)
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_serial: Mapped[str | None] = mapped_column(String(128), nullable=True)
    normalized_serial: Mapped[str | None] = mapped_column(String(128), nullable=True)
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    match_result: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
