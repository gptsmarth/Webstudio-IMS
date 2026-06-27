"""Reusable ORM mixins aligned with DATABASE_DESIGN §11."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class PrimaryKeyMixin:
    """Surrogate BIGINT primary key (DATABASE_DESIGN AD-01)."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class UuidPrimaryKeyMixin:
    """UUID primary key for ProductModel (Sprint 1C)."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Automatic created/updated timestamps (DATABASE_DESIGN §11.3)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
