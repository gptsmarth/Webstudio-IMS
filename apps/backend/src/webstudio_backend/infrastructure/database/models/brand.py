"""Brand ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class Brand(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logo_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # EAN-as-serial mode: when true, inventory units of this brand may share the
    # same serial value (the EAN) — one physical unit per row, uniqueness relaxed.
    # Existing brands default to false (normal, globally-unique serials).
    allow_duplicate_serials: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
