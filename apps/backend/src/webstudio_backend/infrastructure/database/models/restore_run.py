"""Restore run persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class RestoreRun(Base, PrimaryKeyMixin):
    __tablename__ = "restore_runs"

    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    restore_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="entire_database"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    emergency_backup_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
