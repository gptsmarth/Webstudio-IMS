"""Shared repository field validation."""

from __future__ import annotations

from webstudio_backend.infrastructure.repositories.exceptions import RequiredFieldError

MAX_NAME_LENGTH = 128


def normalize_required_name(name: str, *, field: str = "name") -> str:
    if name is None:
        raise RequiredFieldError(field)

    normalized = name.strip()
    if not normalized:
        raise RequiredFieldError(field)
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValueError(f"{field} must be at most {MAX_NAME_LENGTH} characters")
    return normalized
