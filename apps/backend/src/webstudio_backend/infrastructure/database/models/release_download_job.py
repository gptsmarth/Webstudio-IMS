"""GitHub release download job ORM entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    RELEASE_CHANNEL_ENUM_NAME,
    RELEASE_DOWNLOAD_STATUS_ENUM_NAME,
    ReleaseChannel,
    ReleaseDownloadStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class ReleaseDownloadJob(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "release_download_jobs"
    __table_args__ = (
        UniqueConstraint(
            "github_release_id",
            "release_channel",
            name="uq_release_download_jobs_github_channel",
        ),
        {"schema": DATABASE_SCHEMA},
    )

    github_release_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tag_name: Mapped[str] = mapped_column(String(64), nullable=False)
    release_version: Mapped[str] = mapped_column(String(32), nullable=False)
    build_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    status: Mapped[ReleaseDownloadStatus] = mapped_column(
        Enum(
            ReleaseDownloadStatus,
            name=RELEASE_DOWNLOAD_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ReleaseDownloadStatus.PENDING,
    )
    bundle_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    manifest_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checksums_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts: Mapped[list[ReleaseDownloadArtifact]] = relationship(
        "ReleaseDownloadArtifact",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ReleaseDownloadArtifact(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "release_download_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "artifact_name",
            name="uq_release_download_artifacts_job_artifact",
        ),
        {"schema": DATABASE_SCHEMA},
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.release_download_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_name: Mapped[str] = mapped_column(String(256), nullable=False)
    github_asset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    partial_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    bytes_downloaded: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[ReleaseDownloadStatus] = mapped_column(
        Enum(
            ReleaseDownloadStatus,
            name=RELEASE_DOWNLOAD_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_constraint=False,
        ),
        nullable=False,
        default=ReleaseDownloadStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job: Mapped[ReleaseDownloadJob] = relationship("ReleaseDownloadJob", back_populates="artifacts")
