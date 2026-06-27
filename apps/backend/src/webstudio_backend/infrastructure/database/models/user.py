"""User ORM entity."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    THEME_PREFERENCE_ENUM_NAME,
    USER_ROLE_ENUM_NAME,
    USER_STATUS_ENUM_NAME,
    ThemePreference,
    UserRole,
    UserStatus,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class User(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name=USER_ROLE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name=USER_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    theme_preference: Mapped[ThemePreference | None] = mapped_column(
        Enum(
            ThemePreference,
            name=THEME_PREFERENCE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_users_created_by_user"),
        nullable=True,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_users_updated_by_user"),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_key_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recovery_key_last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
