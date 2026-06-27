"""JWT access token utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from webstudio_backend.infrastructure.database.enums import UserRole


class TokenError(Exception):
    """Invalid or expired JWT."""


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: UserRole,
    permissions: list[str],
    token_version: int,
    secret: str,
    issuer: str,
    audience: str,
    expires_minutes: int,
) -> tuple[str, int]:
    expires_in = expires_minutes * 60
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role.value,
        "permissions": permissions,
        "token_version": token_version,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, expires_in


def decode_access_token(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=issuer,
            audience=audience,
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid access token") from exc
