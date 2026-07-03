"""Tally synchronization run history — one row per sync cycle."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class TallySyncHistory(Base, PrimaryKeyMixin):
    __tablename__ = "tally_sync_history"

    tally_company_sync_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.tally_company_sync.id", name="fk_tally_sync_history_company_sync"
        ),
        nullable=False,
    )
    sync_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoices_checked: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    invoices_imported: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    invoices_skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="running")
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
