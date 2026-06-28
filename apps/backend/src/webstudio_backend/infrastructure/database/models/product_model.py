"""ProductModel ORM entity."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    PRODUCT_MODEL_STATUS_ENUM_NAME,
    STORAGE_TYPE_ENUM_NAME,
    STORAGE_UNIT_ENUM_NAME,
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
    model_number: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    cpu: Mapped[str] = mapped_column(String(128), nullable=False)
    gpu: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    storage_unit: Mapped[StorageUnit] = mapped_column(
        Enum(
            StorageUnit,
            name=STORAGE_UNIT_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    storage_type: Mapped[StorageType] = mapped_column(
        Enum(
            StorageType,
            name=STORAGE_TYPE_ENUM_NAME,
            schema=DATABASE_SCHEMA,
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
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
