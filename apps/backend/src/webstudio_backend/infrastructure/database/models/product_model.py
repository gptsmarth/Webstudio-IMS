"""ProductModel ORM entity."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    ACCESSORY_KIND_ENUM_NAME,
    PRODUCT_CATEGORY_ENUM_NAME,
    PRODUCT_MODEL_STATUS_ENUM_NAME,
    STORAGE_TYPE_ENUM_NAME,
    STORAGE_UNIT_ENUM_NAME,
    AccessoryKind,
    ProductCategory,
    ProductModelStatus,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.mixins import TimestampMixin, UuidPrimaryKeyMixin


class ProductModel(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_models"

    brand_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.brands.id", name="fk_product_models_brand"),
        nullable=False,
    )
    category: Mapped[ProductCategory] = mapped_column(
        Enum(
            ProductCategory,
            name=PRODUCT_CATEGORY_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=ProductCategory.LAPTOP.value,
    )
    accessory_kind: Mapped[AccessoryKind | None] = mapped_column(
        Enum(
            AccessoryKind,
            name=ACCESSORY_KIND_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    part_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_number: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    cpu: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gpu: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ram_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    storage_unit: Mapped[StorageUnit | None] = mapped_column(
        Enum(
            StorageUnit,
            name=STORAGE_UNIT_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    storage_type: Mapped[StorageType | None] = mapped_column(
        Enum(
            StorageType,
            name=STORAGE_TYPE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    status: Mapped[ProductModelStatus] = mapped_column(
        Enum(
            ProductModelStatus,
            name=PRODUCT_MODEL_STATUS_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=ProductModelStatus.ACTIVE.value,
    )
    display: Mapped[str | None] = mapped_column(String(128), nullable=True)
    color_options: Mapped[str | None] = mapped_column(String(256), nullable=True)
    product_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    search_aliases: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # ASUS-only live price tracking (Gemini search grounding, see
    # services/asus_live_price_service.py). live_price holds the last
    # SUCCESSFUL lookup; checked_at (every attempt) is separate from
    # updated_at (only successful changes) so a failed refresh never erases
    # a still-useful last-known price.
    live_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    live_price_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    live_price_source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    live_price_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    live_price_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
