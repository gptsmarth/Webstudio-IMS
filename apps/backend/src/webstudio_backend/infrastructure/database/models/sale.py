"""Sale ORM entity — immutable sales history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    SALE_SOURCE_ENUM_NAME,
    SaleSource,
)
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin


class Sale(Base, PrimaryKeyMixin):
    __tablename__ = "sales"

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{DATABASE_SCHEMA}.inventory_items.id",
            name="fk_sales_inventory_item",
        ),
        nullable=False,
        unique=True,
    )
    sale_source: Mapped[SaleSource] = mapped_column(
        Enum(
            SaleSource,
            name=SALE_SOURCE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payment_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sale_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tally_company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tally_voucher_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    printed_invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tally_voucher_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_master_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_voucher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapped_location_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
