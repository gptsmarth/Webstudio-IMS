"""SystemSetting ORM entity."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    SETTING_VALUE_TYPE_ENUM_NAME,
    SettingValueType,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class SystemSetting(PrimaryKeyMixin, Base):
    __tablename__ = "system_settings"

    setting_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[SettingValueType] = mapped_column(
        Enum(
            SettingValueType,
            name=SETTING_VALUE_TYPE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.users.id",
            name="fk_system_settings_updated_by_user",
        ),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
