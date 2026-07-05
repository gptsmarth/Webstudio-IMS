"""ProductModel API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    ProductCategory,
    ProductModelStatus,
    StorageType,
    StorageUnit,
)


class CreateProductModelRequest(BaseModel):
    brand_id: int = Field(gt=0)
    category: ProductCategory = Field(default=ProductCategory.LAPTOP)
    accessory_kind: AccessoryKind | None = None
    part_number: str | None = Field(default=None, min_length=1, max_length=64)
    model_number: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    cpu: str | None = Field(default=None, min_length=1, max_length=128)
    gpu: str | None = Field(default=None, min_length=1, max_length=128)
    ram_gb: int | None = Field(default=None, gt=0)
    storage_value: Decimal | None = Field(default=None, gt=0)
    storage_unit: StorageUnit | None = Field(default=None)
    storage_type: StorageType | None = Field(default=None)
    status: ProductModelStatus = Field(default=ProductModelStatus.ACTIVE)
    display: str | None = Field(default=None, min_length=1, max_length=128)
    color_options: str | None = Field(default=None, min_length=1, max_length=256)
    product_image_url: str | None = Field(default=None, min_length=1, max_length=512)
    search_aliases: str | None = Field(default=None, min_length=1, max_length=1024)
    notes: str | None = Field(default=None, min_length=1, max_length=2000)
    purchase_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_category_fields(self) -> CreateProductModelRequest:
        if self.category == ProductCategory.LAPTOP:
            if not self.cpu:
                raise ValueError("cpu is required for laptops")
            if self.ram_gb is None:
                raise ValueError("ram_gb is required for laptops")
            if self.storage_value is None:
                raise ValueError("storage_value is required for laptops")
            if self.storage_unit is None:
                raise ValueError("storage_unit is required for laptops")
            if self.storage_type is None:
                raise ValueError("storage_type is required for laptops")
        elif self.accessory_kind is None:
            raise ValueError("accessory_kind is required for accessories")
        return self


class UpdateProductModelRequest(BaseModel):
    brand_id: int | None = Field(default=None, gt=0)
    category: ProductCategory | None = None
    accessory_kind: AccessoryKind | None = None
    part_number: str | None = Field(default=None, min_length=1, max_length=64)
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


class AccessorySpecLookupRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=64)
    identifier_type: Literal["part_number", "model_number"] = "model_number"
    brand_name: str | None = Field(default=None, max_length=128)
    accessory_kind: AccessoryKind | None = None
    model_name: str | None = Field(default=None, max_length=128)


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
    provider: str | None = None
    confidence_score: float | None = None
    cached: bool = False


class AccessorySpecLookupResponse(BaseModel):
    model_name: str
    model_number: str | None = None
    part_number: str | None = None
    accessory_kind: AccessoryKind | None = None
    color_options: str | None = None
    product_image_url: str | None = None
    description: str | None = None
    notes: str | None = None
    source: str = "gemini"
    provider: str | None = None
    confidence_score: float | None = None
    cached: bool = False


class ProductModelImageResolveResponse(BaseModel):
    product_image_url: str | None
    source: str = "resolved"


class ProductModelResponse(BaseModel):
    id: uuid.UUID
    brand_id: int
    brand_name: str | None = None
    category: ProductCategory
    accessory_kind: AccessoryKind | None = None
    part_number: str | None = None
    model_number: str
    model_name: str
    cpu: str | None
    gpu: str | None
    ram_gb: int | None
    storage_value: Decimal | None
    storage_unit: StorageUnit | None
    storage_type: StorageType | None
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
            category=pm.category,
            accessory_kind=pm.accessory_kind,
            part_number=pm.part_number,
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
            purchase_price=(
                float(pm.purchase_price)
                if include_purchase_price and pm.purchase_price is not None
                else None
            ),
            selling_price=float(pm.selling_price) if pm.selling_price is not None else None,
            created_at=pm.created_at,
            updated_at=pm.updated_at,
        )
