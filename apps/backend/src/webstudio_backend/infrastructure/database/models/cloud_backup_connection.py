"""Cloud backup provider connection (Google Drive account link)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class CloudBackupConnection(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cloud_backup_connections"

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    account_email: Mapped[str] = mapped_column(String(256), nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    drive_folder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retention_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=25)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="connected")
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.users.id",
            name="fk_cloud_backup_connections_connected_by",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
