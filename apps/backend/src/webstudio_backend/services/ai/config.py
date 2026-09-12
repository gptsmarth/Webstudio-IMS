"""Resolve AI provider configuration from database settings and environment."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.types import AIProviderConfig, ProviderCredentials, ProviderId

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_PRIMARY_PROVIDER: ProviderId = "gemini"
DEFAULT_FALLBACK_CHAIN: list[ProviderId] = ["gemini"]


def provider_has_api_key(config: AIProviderConfig, provider_id: ProviderId) -> bool:
    keys: dict[ProviderId, str] = {
        "gemini": config.gemini.api_key,
        "openai": config.openai.api_key,
        "groq": config.groq.api_key,
        "openrouter": config.openrouter.api_key,
        "mock": "mock",
    }
    if provider_id == "mock":
        return True
    return bool(keys.get(provider_id, "").strip())


def filter_configured_fallback_chain(config: AIProviderConfig) -> list[ProviderId]:
    """Only providers with API keys participate in spec lookup."""
    chain = [
        provider for provider in config.fallback_chain if provider_has_api_key(config, provider)
    ]
    if chain:
        return chain
    if provider_has_api_key(config, config.primary_provider):
        return [config.primary_provider]
    return []


def mask_api_key(api_key: str) -> str | None:
    trimmed = api_key.strip()
    if not trimmed:
        return None
    if len(trimmed) <= 4:
        return "••••"
    return f"{'•' * 8}{trimmed[-4:]}"


VALID_PROVIDERS: tuple[ProviderId, ...] = ("gemini", "openai", "groq", "openrouter", "mock")


def _parse_provider(
    value: str | None, *, default: ProviderId = DEFAULT_PRIMARY_PROVIDER
) -> ProviderId:
    token = (value or default).strip().lower()
    if token in VALID_PROVIDERS:
        return token  # type: ignore[return-value]
    return default


def _parse_fallback_chain(raw: str | None) -> list[ProviderId]:
    if not raw:
        return list(DEFAULT_FALLBACK_CHAIN)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [part.strip() for part in raw.split(",") if part.strip()]
    if not isinstance(parsed, list):
        return list(DEFAULT_FALLBACK_CHAIN)
    chain: list[ProviderId] = []
    for item in parsed:
        provider = _parse_provider(str(item), default=DEFAULT_PRIMARY_PROVIDER)
        if provider not in chain:
            chain.append(provider)
    return chain or list(DEFAULT_FALLBACK_CHAIN)


async def resolve_ai_config(session: AsyncSession, app_settings: Settings) -> AIProviderConfig:
    repo = SystemSettingRepository(session)

    gemini_key = (
        await repo.get_string("gemini_api_key") or ""
    ).strip() or app_settings.gemini_api_key.strip()
    gemini_model = (
        (await repo.get_string("gemini_model") or "").strip()
        or app_settings.gemini_model.strip()
        or DEFAULT_GEMINI_MODEL
    )

    groq_key = (
        await repo.get_string("groq_api_key") or ""
    ).strip() or app_settings.groq_api_key.strip()
    groq_model = (await repo.get_string("groq_model") or "").strip() or DEFAULT_GROQ_MODEL

    openrouter_key = (await repo.get_string("openrouter_api_key") or "").strip()
    openrouter_model = (
        await repo.get_string("openrouter_model") or ""
    ).strip() or DEFAULT_OPENROUTER_MODEL

    openai_key = (
        await repo.get_string("openai_api_key") or ""
    ).strip() or app_settings.openai_api_key.strip()
    openai_model = (
        (await repo.get_string("openai_model") or "").strip()
        or app_settings.openai_model.strip()
        or DEFAULT_OPENAI_MODEL
    )

    primary = _parse_provider(await repo.get_string("ai_primary_provider"))
    fallback = _parse_fallback_chain(await repo.get_string("ai_fallback_chain"))
    if primary not in fallback:
        fallback = [primary, *[provider for provider in fallback if provider != primary]]

    enrichment_enabled_raw = await repo.get_string("ai_enrichment_enabled")
    enrichment_enabled = (
        enrichment_enabled_raw.strip().lower() != "false" if enrichment_enabled_raw else True
    )

    timeout_raw = await repo.get_string("ai_timeout_seconds")
    try:
        timeout_seconds = int(timeout_raw) if timeout_raw else 90
    except ValueError:
        timeout_seconds = 90

    retry_raw = await repo.get_string("ai_retry_count")
    try:
        retry_count = int(retry_raw) if retry_raw else 1
    except ValueError:
        retry_count = 1

    draft = AIProviderConfig(
        primary_provider=primary,
        fallback_chain=fallback,
        enrichment_enabled=enrichment_enabled,
        timeout_seconds=max(15, min(timeout_seconds, 300)),
        retry_count=max(0, min(retry_count, 5)),
        gemini=ProviderCredentials(provider="gemini", api_key=gemini_key, model=gemini_model),
        groq=ProviderCredentials(provider="groq", api_key=groq_key, model=groq_model),
        openrouter=ProviderCredentials(
            provider="openrouter",
            api_key=openrouter_key,
            model=openrouter_model,
        ),
        openai=ProviderCredentials(provider="openai", api_key=openai_key, model=openai_model),
    )
    configured_fallback = filter_configured_fallback_chain(draft)
    return AIProviderConfig(
        primary_provider=primary,
        fallback_chain=configured_fallback or fallback,
        enrichment_enabled=draft.enrichment_enabled,
        timeout_seconds=draft.timeout_seconds,
        retry_count=draft.retry_count,
        gemini=draft.gemini,
        groq=draft.groq,
        openrouter=draft.openrouter,
        openai=draft.openai,
    )


async def resolve_gemini_credentials(
    session: AsyncSession, app_settings: Settings
) -> tuple[str, str]:
    """Backward-compatible Gemini credential resolver."""
    config = await resolve_ai_config(session, app_settings)
    return config.gemini.api_key, config.gemini.model


async def resolve_asus_price_gemini_api_key(session: AsyncSession) -> str:
    """Dedicated Gemini API key for ASUS live-price lookups.

    Kept entirely separate from the general `gemini_api_key` (used for spec
    lookup, image resolution, and enrichment) so the two can be configured,
    rotated, rate-limited, or billed independently — e.g. a low-quota key
    just for price checks that can't starve the spec-lookup key, or vice
    versa. There is no fallback to the general key: if this one isn't set,
    ASUS price lookups report `not_configured` even if the general key is.
    """
    repo = SystemSettingRepository(session)
    return (await repo.get_string("asus_price_gemini_api_key") or "").strip()
