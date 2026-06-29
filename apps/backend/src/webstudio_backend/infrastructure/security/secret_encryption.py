"""Encrypt and decrypt integration secrets at rest."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain_text: str, *, secret: str) -> str:
    return _fernet(secret).encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: str, *, secret: str) -> str:
    try:
        return _fernet(secret).decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt stored secret") from exc


def mask_secret(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) <= 4:
        return "••••"
    return f"••••{trimmed[-4:]}"
