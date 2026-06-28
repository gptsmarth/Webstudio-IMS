"""Tally processed invoice line state."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    TALLY_LINE_OUTCOME_ENUM_NAME,
    TALLY_LINE_STATUS_ENUM_NAME,
    TallyLineOutcome,
    TallyLineStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class TallyProcessedInvoiceLine(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tally_processed_invoice_line"

    tally_processed_invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_processed_invoice.id",
            name="fk_tally_processed_invoice_line_invoice",
        ),
        nullable=False,
    )
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stock_item_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line_status: Mapped[TallyLineStatus] = mapped_column(
        Enum(
            TallyLineStatus,
            name=TALLY_LINE_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    line_outcome: Mapped[TallyLineOutcome | None] = mapped_column(
        Enum(
            TallyLineOutcome,
            name=TALLY_LINE_OUTCOME_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
