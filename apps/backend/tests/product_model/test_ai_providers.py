"""Tests for the AI provider framework."""

from __future__ import annotations

import pytest

from webstudio_backend.services.ai.config import (
    _parse_fallback_chain,
    filter_configured_fallback_chain,
    provider_has_api_key,
)
from webstudio_backend.services.ai.enrichment_service import ProductEnrichmentService
from webstudio_backend.services.ai.gemini_model_stats import (
    most_successful_gemini_model,
    record_gemini_model_success,
    reset_gemini_model_stats,
)
from webstudio_backend.services.ai.health import AIProviderHealthTracker
from webstudio_backend.services.ai.providers.factory import build_provider_chain, create_provider
from webstudio_backend.services.ai.providers.mock import MockProvider
from webstudio_backend.services.ai.types import (
    AIProviderConfig,
    AIProviderError,
    ProviderCredentials,
)


def test_parse_fallback_chain_accepts_json_and_csv() -> None:
    assert _parse_fallback_chain('["groq","gemini"]') == ["groq", "gemini"]
    assert _parse_fallback_chain("groq, gemini, openrouter") == ["groq", "gemini", "openrouter"]


@pytest.mark.asyncio
async def test_mock_provider_returns_deterministic_spec() -> None:
    config = AIProviderConfig()
    provider = MockProvider(config)
    result = await provider.enrich_product_spec(
        "MOCK-TEST-001", brand_name="ASUS", model_name="Vivobook"
    )
    assert result.cpu
    assert result.ram_gb in {8, 16, 32}
    assert result.provider == "mock"
    assert result.image_search_query
    assert "official product" in result.image_search_query.lower()


@pytest.mark.asyncio
async def test_mock_provider_test_connection() -> None:
    provider = MockProvider(AIProviderConfig())
    result = await provider.test_connection()
    assert result.success is True
    assert result.provider == "mock"


def test_provider_chain_respects_fallback_order() -> None:
    config = AIProviderConfig(
        primary_provider="groq",
        fallback_chain=["groq", "gemini", "mock"],
    )
    chain = build_provider_chain(config)
    assert [provider.provider_id for provider in chain] == ["groq", "gemini", "mock"]


@pytest.mark.asyncio
async def test_enrichment_service_uses_mock_provider(db_session, test_settings) -> None:
    AIProviderHealthTracker.reset()
    from webstudio_backend.infrastructure.database.enums import SettingValueType
    from webstudio_backend.infrastructure.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    repo = SystemSettingRepository(db_session)
    await repo.set_value("ai_primary_provider", "mock", value_type=SettingValueType.STRING)
    await repo.set_value("ai_fallback_chain", '["mock"]', value_type=SettingValueType.JSON)
    await repo.set_value("ai_enrichment_enabled", "true", value_type=SettingValueType.BOOLEAN)

    service = ProductEnrichmentService(db_session, test_settings)
    result = await service.lookup_laptop_spec("MOCK-UAT-001", brand_name="ASUS")
    assert result["cpu"]
    assert result["provider"] == "mock"
    assert result["source"] == "mock"

    cached = await service.lookup_laptop_spec("MOCK-UAT-001", brand_name="ASUS")
    assert cached["cached"] is True


@pytest.mark.asyncio
async def test_enrichment_service_fallback_to_mock_when_gemini_not_configured(
    db_session, test_settings
) -> None:
    AIProviderHealthTracker.reset()
    from webstudio_backend.infrastructure.database.enums import SettingValueType
    from webstudio_backend.infrastructure.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    repo = SystemSettingRepository(db_session)
    await repo.set_value("gemini_api_key", "", value_type=SettingValueType.STRING)
    await repo.set_value("ai_fallback_chain", '["gemini","mock"]', value_type=SettingValueType.JSON)
    await repo.set_value("ai_enrichment_enabled", "true", value_type=SettingValueType.BOOLEAN)

    service = ProductEnrichmentService(db_session, test_settings)
    result = await service.lookup_laptop_spec("MOCK-FALLBACK-001", brand_name="Dell")
    assert result["provider"] == "mock"


def test_default_ai_config_uses_gemini_primary() -> None:
    from webstudio_backend.services.ai.config import (
        DEFAULT_FALLBACK_CHAIN,
        DEFAULT_PRIMARY_PROVIDER,
    )
    from webstudio_backend.services.ai.types import AIProviderConfig

    config = AIProviderConfig()
    assert DEFAULT_PRIMARY_PROVIDER == "gemini"
    assert DEFAULT_FALLBACK_CHAIN == ["gemini"]
    assert config.primary_provider == "gemini"
    assert config.fallback_chain == ["gemini"]


def test_parse_fallback_chain_defaults_to_gemini() -> None:
    assert _parse_fallback_chain(None) == ["gemini"]
    assert _parse_fallback_chain("") == ["gemini"]


def test_filter_configured_fallback_chain_skips_openai_without_key() -> None:
    config = AIProviderConfig(
        primary_provider="gemini",
        fallback_chain=["gemini", "openai"],
        gemini=ProviderCredentials(provider="gemini", api_key="gem-key", model="gemini-2.5-flash-lite"),
        openai=ProviderCredentials(provider="openai", api_key="", model="gpt-4o-mini"),
    )
    assert filter_configured_fallback_chain(config) == ["gemini"]
    assert provider_has_api_key(config, "openai") is False


def test_gemini_model_stats_prefers_most_successful_model() -> None:
    reset_gemini_model_stats()
    record_gemini_model_success("gemini-2.5-flash-lite")
    record_gemini_model_success("gemini-2.5-flash-lite")
    record_gemini_model_success("gemini-2.5-flash")
    assert most_successful_gemini_model() == "gemini-2.5-flash-lite"
    reset_gemini_model_stats()


@pytest.mark.asyncio
async def test_openai_provider_test_connection_without_key() -> None:
    provider = create_provider("openai", AIProviderConfig())
    result = await provider.test_connection()
    assert result.success is False
    assert result.provider == "openai"


@pytest.mark.asyncio
async def test_enrichment_service_fallback_to_mock_when_groq_not_configured(
    db_session, test_settings
) -> None:
    AIProviderHealthTracker.reset()
    from webstudio_backend.infrastructure.database.enums import SettingValueType
    from webstudio_backend.infrastructure.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    repo = SystemSettingRepository(db_session)
    await repo.set_value("groq_api_key", "", value_type=SettingValueType.STRING)
    await repo.set_value("gemini_api_key", "", value_type=SettingValueType.STRING)
    await repo.set_value("ai_primary_provider", "groq", value_type=SettingValueType.STRING)
    await repo.set_value("ai_fallback_chain", '["groq","mock"]', value_type=SettingValueType.JSON)
    await repo.set_value("ai_enrichment_enabled", "true", value_type=SettingValueType.BOOLEAN)

    service = ProductEnrichmentService(db_session, test_settings)
    result = await service.lookup_laptop_spec("MOCK-GROQ-FALLBACK-001", brand_name="Lenovo")
    assert result["provider"] == "mock"


def test_create_provider_builds_mock() -> None:
    config = AIProviderConfig()
    assert create_provider("mock", config).provider_id == "mock"


def test_ai_provider_error_codes() -> None:
    error = AIProviderError("RATE_LIMITED", "Too many requests", provider="gemini")
    assert error.code == "RATE_LIMITED"
    assert error.provider == "gemini"
