"""Password history ORM entity."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class PasswordHistory(PrimaryKeyMixin, Base):
    __tablename__ = "password_history"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_password_history_user", ondelete="CASCADE"),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
