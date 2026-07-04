"""InventoryItem ORM entity."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    INVENTORY_STATUS_ENUM_NAME,
    InventoryStatus,
)
from webstudio_backend.infrastructure.database.mixins import TimestampMixin, UuidPrimaryKeyMixin


class InventoryItem(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_items"

    serial_number: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    product_model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{DATABASE_SCHEMA}.product_models.id",
            name="fk_inventory_items_product_model",
        ),
        nullable=False,
    )
    color: Mapped[str] = mapped_column(String(64), nullable=False)
    current_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.locations.id",
            name="fk_inventory_items_current_location",
        ),
        nullable=False,
    )
    status: Mapped[InventoryStatus] = mapped_column(
        Enum(
            InventoryStatus,
            name=INVENTORY_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
