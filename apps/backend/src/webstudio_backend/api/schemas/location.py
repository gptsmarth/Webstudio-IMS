"""Location API schemas."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import LocationType


class CreateLocationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    location_type: LocationType
    is_active: bool = Field(default=True)
    sort_order: int | None = Field(default=None, ge=0)
    branch_id: int | None = Field(default=None, gt=0)


class UpdateLocationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    location_type: LocationType | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    sort_order: int | None = Field(default=None, ge=0)
    branch_id: int | None = Field(default=None, gt=0)


class LocationResponse(BaseModel):
    id: int
    name: str
    location_type: LocationType
    is_active: bool
    sort_order: int | None
    branch_id: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, location) -> LocationResponse:
        return cls(
            id=location.id,
            name=location.name,
            location_type=location.location_type,
            is_active=location.is_active,
            sort_order=location.sort_order,
            branch_id=location.branch_id,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
