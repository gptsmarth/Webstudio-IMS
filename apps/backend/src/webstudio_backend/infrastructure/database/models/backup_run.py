"""Backup run persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class BackupRun(Base, PrimaryKeyMixin):
    __tablename__ = "backup_runs"

    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    archive_path: Mapped[str] = mapped_column(Text, nullable=False)
    backup_type: Mapped[str] = mapped_column(String(32), nullable=False, default="full")
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    creator_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_backup_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.backup_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    cloud_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cloud_upload_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cloud_file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
