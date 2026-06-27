"""Brand ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class Brand(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
