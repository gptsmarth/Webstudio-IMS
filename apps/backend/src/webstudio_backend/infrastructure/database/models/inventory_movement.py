"""InventoryMovement ORM entity."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    MOVEMENT_REASON_ENUM_NAME,
    MovementReason,
)
from webstudio_backend.infrastructure.database.mixins import TimestampMixin, UuidPrimaryKeyMixin


class InventoryMovement(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_movements"

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{DATABASE_SCHEMA}.inventory_items.id",
            name="fk_inventory_movements_inventory_item",
        ),
        nullable=False,
    )
    from_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.locations.id",
            name="fk_inventory_movements_from_location",
        ),
        nullable=False,
    )
    to_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.locations.id",
            name="fk_inventory_movements_to_location",
        ),
        nullable=False,
    )
    movement_reason: Mapped[MovementReason] = mapped_column(
        Enum(
            MovementReason,
            name=MOVEMENT_REASON_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
