"""Infrastructure test ORM model — not a business entity."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class InfrastructureProbe(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "_infra_repository_probe"

    label: Mapped[str] = mapped_column(String(128), nullable=False)
