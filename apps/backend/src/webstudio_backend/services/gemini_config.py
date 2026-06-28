"""Resolve Gemini credentials from database settings with environment fallback."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.services.gemini_spec_service import DEFAULT_MODEL


def mask_api_key(api_key: str) -> str | None:
    trimmed = api_key.strip()
    if not trimmed:
        return None
    if len(trimmed) <= 4:
        return "••••"
    return f"{'•' * 8}{trimmed[-4:]}"


async def resolve_gemini_credentials(
    session: AsyncSession,
    app_settings: Settings,
) -> tuple[str, str]:
    repo = SystemSettingRepository(session)
    db_key = (await repo.get_string("gemini_api_key") or "").strip()
    db_model = (await repo.get_string("gemini_model") or "").strip()
    api_key = db_key or app_settings.gemini_api_key.strip()
    model = db_model or app_settings.gemini_model.strip() or DEFAULT_MODEL
    return api_key, model
