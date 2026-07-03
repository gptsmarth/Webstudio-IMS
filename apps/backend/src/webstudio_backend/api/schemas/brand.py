"""Brand API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateBrandRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    short_name: str | None = Field(default=None, min_length=1, max_length=64)
    logo_filename: str | None = Field(default=None, min_length=1, max_length=256)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class UpdateBrandRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    short_name: str | None = Field(default=None, min_length=1, max_length=64)
    logo_filename: str | None = Field(default=None, min_length=1, max_length=256)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = Field(default=None)


class BrandResponse(BaseModel):
    id: int
    name: str
    short_name: str | None
    logo_filename: str | None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, brand) -> BrandResponse:
        return cls(
            id=brand.id,
            name=brand.name,
            short_name=brand.short_name,
            logo_filename=brand.logo_filename,
            display_order=brand.display_order,
            is_active=brand.is_active,
            created_at=brand.created_at,
            updated_at=brand.updated_at,
        )
