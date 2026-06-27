"""Location ORM model."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import LOCATION_TYPE_ENUM_NAME, LocationType
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class Location(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    location_type: Mapped[LocationType] = mapped_column(
        Enum(
            LocationType,
            name=LOCATION_TYPE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
