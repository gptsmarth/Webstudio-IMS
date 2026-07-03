"""Tally synchronization execution log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    TALLY_SYNC_RUN_STATUS_ENUM_NAME,
    TallySyncRunStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class TallySyncLog(Base, PrimaryKeyMixin):
    __tablename__ = "tally_sync_log"

    sync_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    tally_company_sync_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_company_sync.id", name="fk_tally_sync_log_company_sync"
        ),
        nullable=False,
    )
    tally_processed_invoice_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tally_voucher_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_voucher_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    printed_invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voucher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[TallySyncRunStatus] = mapped_column(
        Enum(
            TallySyncRunStatus,
            name=TALLY_SYNC_RUN_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    inventory_item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    successfully_updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    already_sold: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    missing_serial: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    missing_model: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    model_mismatches: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ignored_items: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
