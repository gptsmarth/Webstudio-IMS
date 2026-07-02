"""Catalogue entity deletion preview and request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BrandDeletePreviewResponse(BaseModel):
    product_model_count: int
    inventory_count: int
    can_delete: bool


class ProductModelDeletePreviewResponse(BaseModel):
    inventory_count: int
    can_delete: bool


class DeleteLocationRequest(BaseModel):
    transfer_to_location_id: int | None = Field(default=None, gt=0)


class LocationDeletePreviewResponse(BaseModel):
    inventory_count: int
    movable_inventory_count: int
    requires_transfer: bool
