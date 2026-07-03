"""Enterprise software release catalog ORM entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    RELEASE_CHANNEL_ENUM_NAME,
    ReleaseChannel,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class SoftwareRelease(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "software_releases"
    __table_args__ = (
        UniqueConstraint(
            "release_version",
            "build_number",
            "release_channel",
            name="uq_software_releases_version_build_channel",
        ),
        {"schema": DATABASE_SCHEMA},
    )

    release_version: Mapped[str] = mapped_column(String(32), nullable=False)
    build_number: Mapped[int] = mapped_column(Integer, nullable=False)
    release_channel: Mapped[ReleaseChannel] = mapped_column(
        Enum(
            ReleaseChannel,
            name=RELEASE_CHANNEL_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    git_short: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    build_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    compatibility_matrix: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    supported_platforms: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
