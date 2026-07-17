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
    INVENTORY_SOURCE_ENUM_NAME,
    INVENTORY_STATUS_ENUM_NAME,
    InventorySource,
    InventoryStatus,
)
from webstudio_backend.infrastructure.database.mixins import TimestampMixin, UuidPrimaryKeyMixin


class InventoryItem(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_items"

    # Uniqueness is NOT declared here: it is a partial unique index in the DB
    # (unique only WHERE serial_is_shared = false). See migration 0053.
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False)
    # True for EAN-as-serial units (brand.allow_duplicate_serials) — these may
    # share a serial value and are excluded from the unique index.
    serial_is_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
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
    inventory_source: Mapped[InventorySource] = mapped_column(
        Enum(
            InventorySource,
            name=INVENTORY_SOURCE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=InventorySource.MANUAL,
        server_default=InventorySource.MANUAL.value,
    )
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
