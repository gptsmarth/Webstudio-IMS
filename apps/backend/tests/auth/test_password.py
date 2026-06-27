"""Password hashing tests."""

from __future__ import annotations

import pytest

from webstudio_backend.infrastructure.security.password import (
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    password_hash = hash_password("SecurePass123!")
    assert password_hash != "SecurePass123!"
    assert verify_password(password_hash, "SecurePass123!")
    assert not verify_password(password_hash, "WrongPassword1!")


def test_validate_password_strength_rejects_short_password() -> None:
    with pytest.raises(ValueError):
        validate_password_strength("short")
