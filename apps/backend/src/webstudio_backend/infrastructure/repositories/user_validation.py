"""User validation helpers."""

from __future__ import annotations

import re

from webstudio_backend.infrastructure.database.enums import HUMAN_USER_ROLES, UserRole

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,64}$")


def normalize_username(username: str) -> str:
    normalized = username.strip()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must be 3-64 alphanumeric characters or underscores")
    return normalized


def validate_human_role(role: UserRole) -> None:
    if role not in HUMAN_USER_ROLES:
        raise ValueError("Invalid role for human user account")
