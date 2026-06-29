"""Encrypted integration API key storage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class IntegrationApiKey(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_api_keys"

    service_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    key_hint: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_integration_api_keys_created_by", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_integration_api_keys_updated_by", ondelete="SET NULL"),
        nullable=True,
    )
