"""Enterprise rollback run tracking — permanent audit history (M13F)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import RELEASE_CHANNEL_ENUM_NAME, ReleaseChannel
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class EnterpriseRollbackRun(PrimaryKeyMixin, TimestampMixin, Base):
    """Permanent rollback audit record — never deleted."""

    __tablename__ = "enterprise_rollback_runs"
    __table_args__ = {"schema": DATABASE_SCHEMA}

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
    from_release_version: Mapped[str] = mapped_column(String(32), nullable=False)
    from_build_number: Mapped[int] = mapped_column(Integer, nullable=False)
    from_release_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    to_release_version: Mapped[str] = mapped_column(String(32), nullable=False)
    to_build_number: Mapped[int] = mapped_column(Integer, nullable=False)
    to_release_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deployment_run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deployment_event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pre_rollback_backup_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    database_restore_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    scheduler_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    config_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_config_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_bundle_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_status: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    performed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
