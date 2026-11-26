"""Laptop comparison payloads."""

import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExternalLaptopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brand: str = Field(min_length=1, max_length=80)
    model_number: str = Field(min_length=1, max_length=160)

    @field_validator("brand", "model_number", mode="before")
    @classmethod
    def clean_identifier(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = " ".join(unicodedata.normalize("NFKC", value).split())
        if not any(char.isalnum() for char in value) or any(
            not (char.isalnum() or char in " .-_/()+&,'#") for char in value
        ):
            raise ValueError("Enter the manufacturer and complete model number.")
        return value


class ComparisonSpec(BaseModel):
    component: str = Field(min_length=1, max_length=90)
    detail: str = Field(min_length=1, max_length=8000)


class ComparisonLaptop(BaseModel):
    source: Literal["inventory", "external"]
    model_id: UUID | None = None
    brand: str = Field(min_length=1, max_length=128)
    model_number: str = Field(min_length=1, max_length=160)
    model_name: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=2048)
    managed_image: bool = False
    available_units: int | None = None
    selling_price: str | None = None
    saved_notes: str | None = None
    specifications: list[ComparisonSpec] = Field(max_length=60)
