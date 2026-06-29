"""Password hashing and verification using Argon2id."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def validate_password_strength(password: str) -> None:
    """Synchronous validation using default policy — prefer PasswordPolicyService in async code."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include a lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include a number")
