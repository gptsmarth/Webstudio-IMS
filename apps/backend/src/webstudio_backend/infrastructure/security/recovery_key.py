"""Main Admin recovery key generation and verification."""

from __future__ import annotations

import re
import secrets

from webstudio_backend.infrastructure.security.password import hash_password, verify_password

_RECOVERY_KEY_PATTERN = re.compile(r"^[A-F0-9]{4}(?:-[A-F0-9]{4}){3}$")


def generate_recovery_key() -> str:
    """Generate a printable, cryptographically secure recovery key."""
    raw = secrets.token_hex(8).upper()
    return "-".join(raw[index : index + 4] for index in range(0, len(raw), 4))


def normalize_recovery_key(recovery_key: str) -> str:
    cleaned = recovery_key.strip().upper().replace(" ", "")
    if "-" not in cleaned and len(cleaned) == 16:
        cleaned = "-".join(cleaned[index : index + 4] for index in range(0, len(cleaned), 4))
    if not _RECOVERY_KEY_PATTERN.fullmatch(cleaned):
        raise ValueError("Invalid recovery key format")
    return cleaned


def hash_recovery_key(recovery_key: str) -> str:
    return hash_password(normalize_recovery_key(recovery_key))


def verify_recovery_key(recovery_key_hash: str | None, recovery_key: str) -> bool:
    if recovery_key_hash is None:
        return False
    try:
        normalized = normalize_recovery_key(recovery_key)
    except ValueError:
        return False
    return verify_password(recovery_key_hash, normalized)
