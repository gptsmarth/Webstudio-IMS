"""Integration API key schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IntegrationKeySummary(BaseModel):
    id: int
    service_type: str
    label: str
    key_hint: str | None = None
    is_active: bool
    is_archived: bool
    created_at: str
    updated_at: str


class CreateIntegrationKeyRequest(BaseModel):
    service_type: str = Field(..., min_length=1, max_length=32)
    label: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=1)


class UpdateIntegrationKeyRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=128)
    api_key: str | None = Field(default=None, min_length=1)
