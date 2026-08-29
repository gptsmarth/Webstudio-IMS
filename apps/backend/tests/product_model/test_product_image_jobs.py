"""Tests for the Gemini image-discovery fallback and job concurrency cap."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services import product_image_jobs
from webstudio_backend.services.ai.providers import gemini as gemini_module
from webstudio_backend.services.product_image_jobs import (
    _MAX_CONCURRENT_IMAGE_JOBS,
    _concurrency_limiter,
    _try_gemini_image_fallback,
)


@pytest.mark.asyncio
async def test_gemini_fallback_skips_when_not_configured(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    # No gemini_api_key set anywhere — must return None without attempting any network call.
    result = await _try_gemini_image_fallback(
        db_session,
        model_number="TEST-001",
        brand_name="ASUS",
        model_name="Test Laptop",
        model_id="00000000-0000-0000-0000-000000000000",
        image_query="ASUS Test Laptop TEST-001",
    )
    assert result is None


@pytest.mark.asyncio
async def test_gemini_fallback_uses_grounding_when_configured(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await SystemSettingRepository(db_session).set_value(
        "gemini_api_key", "fake-key-for-test", value_type=SettingValueType.STRING
    )
    await db_session.commit()

    async def fake_grounding(self, model_number, *, brand_name=None, model_name=None):
        return {"candidates": [{"groundingMetadata": {"groundingChunks": []}}]}

    monkeypatch.setattr(gemini_module.GeminiProvider, "find_image_page_grounding", fake_grounding)

    captured: dict[str, object] = {}

    async def fake_resolve_product_image(**kwargs):
        captured.update(kwargs)
        return "https://example-cdn.test/found.jpg"

    monkeypatch.setattr(product_image_jobs, "resolve_product_image", fake_resolve_product_image)

    result = await _try_gemini_image_fallback(
        db_session,
        model_number="TEST-002",
        brand_name="ASUS",
        model_name="Test Laptop 2",
        model_id="00000000-0000-0000-0000-000000000001",
        image_query="ASUS Test Laptop 2 TEST-002",
    )
    assert result == "https://example-cdn.test/found.jpg"
    assert captured["model_number"] == "TEST-002"
    assert captured["grounding_body"] is not None


@pytest.mark.asyncio
async def test_gemini_fallback_returns_none_when_grounding_empty(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await SystemSettingRepository(db_session).set_value(
        "gemini_api_key", "fake-key-for-test", value_type=SettingValueType.STRING
    )
    await db_session.commit()

    async def fake_grounding_none(self, model_number, *, brand_name=None, model_name=None):
        return None

    monkeypatch.setattr(
        gemini_module.GeminiProvider, "find_image_page_grounding", fake_grounding_none
    )

    result = await _try_gemini_image_fallback(
        db_session,
        model_number="TEST-003",
        brand_name=None,
        model_name=None,
        model_id="00000000-0000-0000-0000-000000000002",
        image_query="TEST-003",
    )
    assert result is None


@pytest.mark.asyncio
async def test_gemini_fallback_never_raises_on_unexpected_error(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await SystemSettingRepository(db_session).set_value(
        "gemini_api_key", "fake-key-for-test", value_type=SettingValueType.STRING
    )
    await db_session.commit()

    async def raise_error(self, model_number, *, brand_name=None, model_name=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(gemini_module.GeminiProvider, "find_image_page_grounding", raise_error)

    result = await _try_gemini_image_fallback(
        db_session,
        model_number="TEST-004",
        brand_name=None,
        model_name=None,
        model_id="00000000-0000-0000-0000-000000000003",
        image_query="TEST-004",
    )
    assert result is None


@pytest.mark.asyncio
async def test_image_job_concurrency_is_capped() -> None:
    assert _MAX_CONCURRENT_IMAGE_JOBS == 3
    assert _concurrency_limiter.locked() is False
    # Acquiring exactly the cap's worth of permits must exhaust it.
    for _ in range(_MAX_CONCURRENT_IMAGE_JOBS):
        await _concurrency_limiter.acquire()
    assert _concurrency_limiter.locked() is True
    for _ in range(_MAX_CONCURRENT_IMAGE_JOBS):
        _concurrency_limiter.release()
    assert _concurrency_limiter.locked() is False
