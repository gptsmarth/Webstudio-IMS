"""ASUS-only live price lookup (Gemini search grounding). Additive feature.

Proves refresh_asus_live_price:
  * no-ops for non-ASUS brands without ever calling Gemini,
  * degrades gracefully (never raises) for every failure mode,
  * rejects a price sourced from anywhere but an asus.com domain even if
    the model claims otherwise (defense-in-depth against prompt non-compliance),
  * never erases a previously-successful price on a later failed attempt.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    SettingValueType,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.providers import gemini as gemini_module
from webstudio_backend.services.asus_live_price_jobs import (
    _DEFAULT_STALE_AFTER_DAYS,
    _MAX_CONCURRENT_ASUS_PRICE_JOBS,
    _MAX_STALE_AFTER_DAYS,
    _MIN_STALE_AFTER_DAYS,
    _concurrency_limiter,
    _get_stale_after_days,
)
from webstudio_backend.services.asus_live_price_service import refresh_asus_live_price


async def _make_model(db_session: AsyncSession, brand_id: int, model_number: str):
    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand_id,
        model_number=model_number,
        model_name="Test Laptop",
        cpu="Intel",
        gpu="Intel",
        ram_gb=8,
        storage_value=Decimal("256"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()
    return model


async def _configure_gemini(db_session: AsyncSession) -> None:
    await SystemSettingRepository(db_session).set_value(
        "gemini_api_key", "fake-key-for-test", value_type=SettingValueType.STRING
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_non_asus_brand_never_calls_gemini(
    db_session: AsyncSession, test_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    other_brand = await BrandRepository(db_session).create("HP")
    await db_session.commit()
    model = await _make_model(db_session, other_brand.id, "HP-001")
    await _configure_gemini(db_session)

    async def fail_if_called(self, *args, **kwargs):
        raise AssertionError("Gemini should never be called for a non-ASUS model")

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fail_if_called)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_applicable"


@pytest.mark.asyncio
async def test_no_gemini_key_configured(db_session: AsyncSession, test_settings, brand) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-001")
    # No gemini_api_key set anywhere.
    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_configured"
    await db_session.refresh(model)
    assert model.live_price_status == "not_configured"
    assert model.live_price is None


@pytest.mark.asyncio
async def test_provider_failure_maps_to_error(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-002")
    await _configure_gemini(db_session)

    async def fake_none(self, model_number, *, brand_name=None, model_name=None):
        return None

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_none)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "error"


@pytest.mark.asyncio
async def test_low_confidence_treated_as_not_found(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-003")
    await _configure_gemini(db_session)

    async def fake_low_confidence(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 50000,
            "source_url": "https://in.store.asus.com/some-page.html",
            "confidence": "low",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_low_confidence)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_found"
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_non_asus_source_domain_rejected_even_if_high_confidence(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defense-in-depth: never trust the LLM's domain compliance alone."""
    model = await _make_model(db_session, brand.id, "ASUS-004")
    await _configure_gemini(db_session)

    async def fake_retailer_source(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 45000,
            "source_url": "https://www.amazon.in/dp/example",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_retailer_source)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_found"
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_successful_lookup_stores_price_and_source(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-005")
    await _configure_gemini(db_session)

    async def fake_success(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 81990.0,
            "source_url": "https://in.store.asus.com/vivobook-16-m1605naq-mb095ws.html",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_success)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "ok"
    await db_session.refresh(model)
    assert model.live_price == Decimal("81990.00")
    assert model.live_price_source_url == (
        "https://in.store.asus.com/vivobook-16-m1605naq-mb095ws.html"
    )
    assert model.live_price_status == "ok"
    assert model.live_price_checked_at is not None
    assert model.live_price_updated_at is not None


@pytest.mark.asyncio
async def test_failed_attempt_never_erases_previous_successful_price(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-006")
    await _configure_gemini(db_session)

    async def fake_success(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 70000,
            "source_url": "https://in.store.asus.com/some-model.html",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_success)
    first_status = await refresh_asus_live_price(db_session, model.id)
    assert first_status == "ok"
    await db_session.refresh(model)
    first_updated_at = model.live_price_updated_at
    assert model.live_price == Decimal("70000")

    async def fake_failure(self, model_number, *, brand_name=None, model_name=None):
        return None

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_failure)
    second_status = await refresh_asus_live_price(db_session, model.id)
    assert second_status == "error"

    await db_session.refresh(model)
    # Price and its own updated_at are untouched by the failed attempt...
    assert model.live_price == Decimal("70000")
    assert model.live_price_updated_at == first_updated_at
    # ...but the attempt itself, and the now-"error" status, are recorded.
    assert model.live_price_status == "error"
    assert model.live_price_checked_at is not None


@pytest.mark.asyncio
async def test_stale_after_days_defaults_when_unset(
    db_session: AsyncSession, test_settings
) -> None:
    assert await _get_stale_after_days(db_session) == _DEFAULT_STALE_AFTER_DAYS


@pytest.mark.asyncio
async def test_stale_after_days_reads_admin_configured_value(
    db_session: AsyncSession, test_settings
) -> None:
    await SystemSettingRepository(db_session).set_value(
        "asus_price_refresh_stale_days", "30", value_type=SettingValueType.INTEGER
    )
    await db_session.commit()
    assert await _get_stale_after_days(db_session) == 30


@pytest.mark.asyncio
async def test_stale_after_days_is_clamped_to_a_sane_range(
    db_session: AsyncSession, test_settings
) -> None:
    settings_repo = SystemSettingRepository(db_session)

    await settings_repo.set_value(
        "asus_price_refresh_stale_days", "0", value_type=SettingValueType.INTEGER
    )
    await db_session.commit()
    assert await _get_stale_after_days(db_session) == _MIN_STALE_AFTER_DAYS

    await settings_repo.set_value(
        "asus_price_refresh_stale_days", "9999", value_type=SettingValueType.INTEGER
    )
    await db_session.commit()
    assert await _get_stale_after_days(db_session) == _MAX_STALE_AFTER_DAYS


@pytest.mark.asyncio
async def test_asus_price_job_concurrency_is_capped() -> None:
    assert _MAX_CONCURRENT_ASUS_PRICE_JOBS == 2
    assert _concurrency_limiter.locked() is False
    for _ in range(_MAX_CONCURRENT_ASUS_PRICE_JOBS):
        await _concurrency_limiter.acquire()
    assert _concurrency_limiter.locked() is True
    for _ in range(_MAX_CONCURRENT_ASUS_PRICE_JOBS):
        _concurrency_limiter.release()
    assert _concurrency_limiter.locked() is False
