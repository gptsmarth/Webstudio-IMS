"""Product model field validation."""

from __future__ import annotations

from decimal import Decimal

from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    ProductCategory,
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


def validate_part_number(part_number: str | None) -> str | None:
    if part_number is None:
        return None
    normalized = part_number.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_MODEL_NUMBER_LENGTH:
        raise InvalidFieldValueError("part_number", f"must be at most {MAX_MODEL_NUMBER_LENGTH} characters")
    return normalized


def validate_category(category: ProductCategory) -> ProductCategory:
    if not isinstance(category, ProductCategory):
        raise InvalidFieldValueError("category", "invalid enum value")
    return category


def validate_accessory_kind(accessory_kind: AccessoryKind | None) -> AccessoryKind | None:
    if accessory_kind is None:
        return None
    if not isinstance(accessory_kind, AccessoryKind):
        raise InvalidFieldValueError("accessory_kind", "invalid enum value")
    return accessory_kind


def validate_cpu(cpu: str | None) -> str | None:
    if cpu is None:
        return None
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


def validate_ram_gb(ram_gb: int | None) -> int | None:
    if ram_gb is None:
        return None
    if ram_gb <= 0:
        raise InvalidFieldValueError("ram_gb", "must be greater than 0")
    return ram_gb


def validate_storage_value(storage_value: Decimal | None) -> Decimal | None:
    if storage_value is None:
        return None
    if storage_value <= 0:
        raise InvalidFieldValueError("storage_value", "must be greater than 0")
    return storage_value


def validate_storage_unit(storage_unit: StorageUnit | None) -> StorageUnit | None:
    if storage_unit is None:
        return None
    if not isinstance(storage_unit, StorageUnit):
        raise InvalidFieldValueError("storage_unit", "invalid enum value")
    return storage_unit


def validate_storage_type(storage_type: StorageType | None) -> StorageType | None:
    if storage_type is None:
        return None
    if not isinstance(storage_type, StorageType):
        raise InvalidFieldValueError("storage_type", "invalid enum value")
    return storage_type


def validate_status(status: ProductModelStatus) -> ProductModelStatus:
    if not isinstance(status, ProductModelStatus):
        raise InvalidFieldValueError("status", "invalid enum value")
    return status


def validate_laptop_configuration(
    *,
    category: ProductCategory,
    cpu: str | None,
    ram_gb: int | None,
    storage_value: Decimal | None,
    storage_unit: StorageUnit | None,
    storage_type: StorageType | None,
    accessory_kind: AccessoryKind | None,
) -> None:
    if category == ProductCategory.LAPTOP:
        if not cpu:
            raise RequiredFieldError("cpu")
        if ram_gb is None:
            raise RequiredFieldError("ram_gb")
        if storage_value is None:
            raise RequiredFieldError("storage_value")
        if storage_unit is None:
            raise RequiredFieldError("storage_unit")
        if storage_type is None:
            raise RequiredFieldError("storage_type")
        return
    if category == ProductCategory.ACCESSORY and accessory_kind is None:
        raise RequiredFieldError("accessory_kind")


def validate_brand_name_for_tests(name: str) -> str:
    return normalize_required_name(name)
