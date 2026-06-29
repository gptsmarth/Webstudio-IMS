"""Resolve Gemini credentials from database settings with environment fallback."""

from __future__ import annotations

from webstudio_backend.services.ai.config import (
    DEFAULT_GEMINI_MODEL,
    mask_api_key,
    resolve_ai_config,
    resolve_gemini_credentials,
)

DEFAULT_MODEL = DEFAULT_GEMINI_MODEL

__all__ = [
    "DEFAULT_MODEL",
    "mask_api_key",
    "resolve_ai_config",
    "resolve_gemini_credentials",
]
