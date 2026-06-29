"""ProductModel API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import (
    ProductModelStatus,
    StorageType,
    StorageUnit,
)


class CreateProductModelRequest(BaseModel):
    brand_id: int = Field(gt=0)
    model_number: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    cpu: str = Field(min_length=1, max_length=128)
    gpu: str | None = Field(default=None, min_length=1, max_length=128)
    ram_gb: int = Field(gt=0)
    storage_value: Decimal = Field(gt=0)
    storage_unit: StorageUnit
    storage_type: StorageType
    status: ProductModelStatus = Field(default=ProductModelStatus.ACTIVE)
    display: str | None = Field(default=None, min_length=1, max_length=128)
    color_options: str | None = Field(default=None, min_length=1, max_length=256)
    product_image_url: str | None = Field(default=None, min_length=1, max_length=512)
    search_aliases: str | None = Field(default=None, min_length=1, max_length=1024)
    notes: str | None = Field(default=None, min_length=1, max_length=2000)
    purchase_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)


class UpdateProductModelRequest(BaseModel):
    brand_id: int | None = Field(default=None, gt=0)
    model_number: str | None = Field(default=None, min_length=1, max_length=64)
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    cpu: str | None = Field(default=None, min_length=1, max_length=128)
    gpu: str | None = Field(default=None, min_length=1, max_length=128)
    ram_gb: int | None = Field(default=None, gt=0)
    storage_value: Decimal | None = Field(default=None, gt=0)
    storage_unit: StorageUnit | None = Field(default=None)
    storage_type: StorageType | None = Field(default=None)
    status: ProductModelStatus | None = Field(default=None)
    display: str | None = Field(default=None, min_length=1, max_length=128)
    color_options: str | None = Field(default=None, min_length=1, max_length=256)
    product_image_url: str | None = Field(default=None, min_length=1, max_length=512)
    search_aliases: str | None = Field(default=None, min_length=1, max_length=1024)
    notes: str | None = Field(default=None, min_length=1, max_length=2000)
    purchase_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)


class UpdateSellingPriceRequest(BaseModel):
    selling_price: Decimal | None = Field(default=None, ge=0)


class ProductModelSpecLookupRequest(BaseModel):
    model_number: str = Field(min_length=1, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    brand_name: str | None = Field(default=None, max_length=128)


class ProductModelSpecLookupResponse(BaseModel):
    model_name: str
    cpu: str
    gpu: str | None
    ram_gb: int
    storage_value: str
    storage_unit: StorageUnit
    storage_type: StorageType
    display: str | None
    color_options: str | None = None
    product_image_url: str | None
    description: str | None = None
    notes: str | None = None
    source: str = "gemini"


class ProductModelImageResolveResponse(BaseModel):
    product_image_url: str | None
    source: str = "resolved"


class ProductModelResponse(BaseModel):
    id: uuid.UUID
    brand_id: int
    brand_name: str | None = None
    model_number: str
    model_name: str
    cpu: str
    gpu: str | None
    ram_gb: int
    storage_value: Decimal
    storage_unit: StorageUnit
    storage_type: StorageType
    status: ProductModelStatus
    display: str | None
    color_options: str | None
    product_image_url: str | None
    search_aliases: str | None
    notes: str | None
    purchase_price: float | None = None
    selling_price: float | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls,
        pm,
        *,
        brand_name: str | None = None,
        include_purchase_price: bool = True,
    ) -> ProductModelResponse:
        return cls(
            id=pm.id,
            brand_id=pm.brand_id,
            brand_name=brand_name,
            model_number=pm.model_number,
            model_name=pm.model_name,
            cpu=pm.cpu,
            gpu=pm.gpu,
            ram_gb=pm.ram_gb,
            storage_value=pm.storage_value,
            storage_unit=pm.storage_unit,
            storage_type=pm.storage_type,
            status=pm.status,
            display=pm.display,
            color_options=pm.color_options,
            product_image_url=pm.product_image_url,
            search_aliases=pm.search_aliases,
            notes=pm.notes,
            purchase_price=float(pm.purchase_price) if include_purchase_price and pm.purchase_price is not None else None,
            selling_price=float(pm.selling_price) if pm.selling_price is not None else None,
            created_at=pm.created_at,
            updated_at=pm.updated_at,
        )
