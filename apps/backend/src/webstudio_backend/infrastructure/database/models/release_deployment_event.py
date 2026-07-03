"""Release deployment event ORM entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    RELEASE_CHANNEL_ENUM_NAME,
    ReleaseChannel,
)


class ReleaseDeploymentEvent(Base):
    __tablename__ = "release_deployment_events"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    release_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    build_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    release_channel: Mapped[ReleaseChannel | None] = mapped_column(
        Enum(
            ReleaseChannel,
            name=RELEASE_CHANNEL_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_constraint=False,
        ),
        nullable=True,
    )
    job_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    release_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    administrator_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    performed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
