"""Product model field validation."""

from __future__ import annotations

from decimal import Decimal

from webstudio_backend.infrastructure.database.enums import (
    ProductModelStatus,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories.exceptions import (
    InvalidFieldValueError,
    RequiredFieldError,
)
from webstudio_backend.infrastructure.repositories.validation import (
    MAX_NAME_LENGTH,
    normalize_required_name,
)

MAX_MODEL_NUMBER_LENGTH = 64
MAX_SPEC_LENGTH = 128


def normalize_required_text(value: str, *, field: str, max_length: int) -> str:
    if value is None:
        raise RequiredFieldError(field)

    normalized = value.strip()
    if not normalized:
        raise RequiredFieldError(field)
    if len(normalized) > max_length:
        raise InvalidFieldValueError(field, f"must be at most {max_length} characters")
    return normalized


def validate_model_number(model_number: str) -> str:
    return normalize_required_text(
        model_number,
        field="model_number",
        max_length=MAX_MODEL_NUMBER_LENGTH,
    )


def validate_model_name(model_name: str) -> str:
    return normalize_required_text(
        model_name,
        field="model_name",
        max_length=MAX_NAME_LENGTH,
    )


def validate_cpu(cpu: str) -> str:
    return normalize_required_text(cpu, field="cpu", max_length=MAX_SPEC_LENGTH)


def validate_gpu(gpu: str | None) -> str | None:
    if gpu is None:
        return None
    normalized = gpu.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_SPEC_LENGTH:
        raise InvalidFieldValueError("gpu", f"must be at most {MAX_SPEC_LENGTH} characters")
    return normalized


def validate_ram_gb(ram_gb: int) -> int:
    if ram_gb <= 0:
        raise InvalidFieldValueError("ram_gb", "must be greater than 0")
    return ram_gb


def validate_storage_value(storage_value: Decimal) -> Decimal:
    if storage_value <= 0:
        raise InvalidFieldValueError("storage_value", "must be greater than 0")
    return storage_value


def validate_storage_unit(storage_unit: StorageUnit) -> StorageUnit:
    if not isinstance(storage_unit, StorageUnit):
        raise InvalidFieldValueError("storage_unit", "invalid enum value")
    return storage_unit


def validate_storage_type(storage_type: StorageType) -> StorageType:
    if not isinstance(storage_type, StorageType):
        raise InvalidFieldValueError("storage_type", "invalid enum value")
    return storage_type


def validate_status(status: ProductModelStatus) -> ProductModelStatus:
    if not isinstance(status, ProductModelStatus):
        raise InvalidFieldValueError("status", "invalid enum value")
    return status


def validate_brand_name_for_tests(name: str) -> str:
    return normalize_required_name(name)
