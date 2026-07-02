"""Tally company sync state."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class TallyCompanySync(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tally_company_sync"

    company_name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_processed_master_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_imported_voucher_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    consecutive_sync_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sync_in_progress: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    last_sync_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_invoices_imported_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="disconnected")
    connectivity_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="offline")
    last_successful_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_resolved_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
