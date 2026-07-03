"""Enterprise deployment run ORM entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    RELEASE_CHANNEL_ENUM_NAME,
    ReleaseChannel,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class ReleaseDeploymentRun(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "release_deployment_runs"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    job_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    release_version: Mapped[str] = mapped_column(String(32), nullable=False)
    build_number: Mapped[int] = mapped_column(Integer, nullable=False)
    release_channel: Mapped[ReleaseChannel] = mapped_column(
        Enum(
            ReleaseChannel,
            name=RELEASE_CHANNEL_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_constraint=False,
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    pre_backup_run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pre_backup_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rollback_backup_run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scheduler_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    config_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_config_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_release_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bundle_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
