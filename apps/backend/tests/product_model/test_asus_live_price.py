"""ASUS-only live price lookup (Gemini search grounding). Additive feature.

Proves refresh_asus_live_price:
  * no-ops for non-ASUS brands without ever calling Gemini,
  * degrades gracefully (never raises) for every failure mode,
  * rejects a price sourced from anywhere but an asus.com domain even if
    the model claims otherwise (defense-in-depth against prompt non-compliance),
  * never erases a previously-successful price on a later failed attempt.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    SettingValueType,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services import asus_live_price_jobs as asus_jobs_module
from webstudio_backend.services import asus_live_price_service as asus_price_service_module
from webstudio_backend.services.ai.providers import gemini as gemini_module
from webstudio_backend.services.asus_live_price_jobs import (
    _DEFAULT_STALE_AFTER_DAYS,
    _MAX_CONCURRENT_ASUS_PRICE_JOBS,
    _MAX_STALE_AFTER_DAYS,
    _MIN_STALE_AFTER_DAYS,
    _concurrency_limiter,
    _get_stale_after_days,
    get_asus_bulk_run_status,
    retry_failed_asus_price_refreshes,
    schedule_all_asus_price_refreshes,
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


async def _add_available_unit(db_session: AsyncSession, product_model_id: uuid.UUID) -> None:
    """Bulk/scheduled ASUS price refresh now skips models with zero available
    stock (cost optimization) — tests that need a model to actually be
    picked up by that sweep must give it at least one available unit."""
    location = await LocationRepository(db_session).create(
        f"Test Location {uuid.uuid4().hex[:8]}", location_type=LocationType.WAREHOUSE
    )
    await db_session.commit()
    await InventoryItemRepository(db_session).create(
        serial_number=f"SN-{uuid.uuid4().hex[:10].upper()}",
        product_model_id=product_model_id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()


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
async def test_general_asus_com_domain_is_not_enough_only_the_india_store_is_accepted(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deliberately narrower than "any asus.com subdomain": ASUS's general
    marketing/spec pages (www.asus.com) don't carry a real purchasable price,
    only in.store.asus.com does — only that exact store domain is accepted."""
    model = await _make_model(db_session, brand.id, "ASUS-012")
    await _configure_gemini(db_session)

    async def fake_general_asus_site(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 89990,
            "source_url": "https://www.asus.com/in/laptops/for-home/vivobook/some-model/",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_general_asus_site)

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_found"
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_accessory_category_never_calls_gemini(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accessories (chargers, adapters, etc.) are explicitly out of scope —
    only ASUS laptops get a live price."""
    from webstudio_backend.infrastructure.database.enums import AccessoryKind, ProductCategory

    accessory = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="AC65-06",
        model_name="65W USB Type-C AC Adapter",
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.ADAPTER,
    )
    await db_session.commit()
    await _configure_gemini(db_session)

    async def fail_if_called(self, *args, **kwargs):
        raise AssertionError("Gemini should never be called for an accessory")

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fail_if_called)

    status = await refresh_asus_live_price(db_session, accessory.id)
    assert status == "not_applicable"


class _FakeRedirectResponse:
    def __init__(self, location: str | None) -> None:
        self.headers = {"location": location} if location else {}


class _FakeRedirectClient:
    """Stands in for httpx.AsyncClient — returns a canned redirect Location
    instead of making a real network call to vertexaisearch.cloud.google.com."""

    def __init__(
        self, *, location: str | None = None, raise_error: bool = False, **_: object
    ) -> None:
        self._location = location
        self._raise_error = raise_error

    async def __aenter__(self) -> _FakeRedirectClient:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def get(self, url: str) -> _FakeRedirectResponse:
        if self._raise_error:
            raise httpx.ConnectTimeout("simulated redirect-resolution failure")
        return _FakeRedirectResponse(self._location)


@pytest.mark.asyncio
async def test_vertexaisearch_redirect_resolving_to_asus_is_accepted(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test: Gemini's Search grounding frequently cites sources
    through Google's own vertexaisearch.cloud.google.com tracking redirect
    rather than the real page URL. A naive domain check on that wrapper URL
    wrongly rejected genuine ASUS-sourced answers — this proves the redirect
    is resolved to its real target before the domain check runs."""
    model = await _make_model(db_session, brand.id, "ASUS-009")
    await _configure_gemini(db_session)

    async def fake_grounded_redirect(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 91990,
            "source_url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/FAKE123",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_grounded_redirect)
    monkeypatch.setattr(
        asus_price_service_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeRedirectClient(
            location="https://in.store.asus.com/real-product-page.html"
        ),
    )

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "ok"
    await db_session.refresh(model)
    assert model.live_price == Decimal("91990")
    assert model.live_price_source_url == "https://in.store.asus.com/real-product-page.html"


@pytest.mark.asyncio
async def test_vertexaisearch_redirect_resolving_to_non_asus_is_still_rejected(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-010")
    await _configure_gemini(db_session)

    async def fake_grounded_redirect(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 45000,
            "source_url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/FAKE456",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_grounded_redirect)
    monkeypatch.setattr(
        asus_price_service_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeRedirectClient(location="https://www.amazon.in/dp/example"),
    )

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_found"
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_vertexaisearch_redirect_resolution_failure_degrades_gracefully(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A network hiccup resolving the redirect must never raise — it should
    just fall back to rejecting, same as before this resolution existed."""
    model = await _make_model(db_session, brand.id, "ASUS-011")
    await _configure_gemini(db_session)

    async def fake_grounded_redirect(self, model_number, *, brand_name=None, model_name=None):
        return {
            "price": 50000,
            "source_url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/FAKE789",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_module.GeminiProvider, "lookup_live_price", fake_grounded_redirect)
    monkeypatch.setattr(
        asus_price_service_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeRedirectClient(raise_error=True),
    )

    status = await refresh_asus_live_price(db_session, model.id)
    assert status == "not_found"


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
        "asus_price_refresh_stale_days", "45", value_type=SettingValueType.INTEGER
    )
    await db_session.commit()
    assert await _get_stale_after_days(db_session) == 45


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


def test_bulk_run_status_defaults_when_never_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    assert get_asus_bulk_run_status() == {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "started_at": None,
        "finished_at": None,
        "failed_model_ids": [],
    }


@pytest.mark.asyncio
async def test_bulk_run_with_no_asus_models_finishes_immediately(
    db_session: AsyncSession, test_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    scheduled = await schedule_all_asus_price_refreshes()
    assert scheduled == 0
    status = get_asus_bulk_run_status()
    assert status["total"] == 0
    assert status["finished_at"] is not None


@pytest.mark.asyncio
async def test_bulk_refresh_skips_out_of_stock_models(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cost optimization: refreshing a model's live price only matters while
    it can actually be sold. An ASUS model with zero available units must be
    skipped by both the bulk "Update prices" trigger and the scheduled sweep,
    so quota isn't spent tracking unsellable stock."""
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    in_stock = await _make_model(db_session, brand.id, "ASUS-INSTOCK")
    out_of_stock = await _make_model(db_session, brand.id, "ASUS-OUTOFSTOCK")
    await _add_available_unit(db_session, in_stock.id)

    repo = ProductModelRepository(db_session)
    ids_for_bulk = await repo.list_ids_for_asus_brand()
    assert in_stock.id in ids_for_bulk
    assert out_of_stock.id not in ids_for_bulk

    ids_for_sweep = await repo.list_ids_needing_asus_price_refresh(
        stale_before=datetime.now(UTC), limit=10
    )
    assert in_stock.id in ids_for_sweep
    assert out_of_stock.id not in ids_for_sweep


@pytest.mark.asyncio
async def test_bulk_and_sweep_exclude_accessories(
    db_session: AsyncSession, test_settings, brand
) -> None:
    """Only ASUS laptops are eligible — an in-stock ASUS accessory must
    never appear in either the bulk "Update prices" list or the scheduled
    sweep's "due" list."""
    from webstudio_backend.infrastructure.database.enums import AccessoryKind, ProductCategory

    laptop = await _make_model(db_session, brand.id, "ASUS-LAPTOP-ONLY")
    await _add_available_unit(db_session, laptop.id)

    accessory = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="AC65-07",
        model_name="65W USB Type-C AC Adapter",
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.ADAPTER,
    )
    await db_session.commit()
    await _add_available_unit(db_session, accessory.id)

    repo = ProductModelRepository(db_session)
    ids_for_bulk = await repo.list_ids_for_asus_brand()
    assert laptop.id in ids_for_bulk
    assert accessory.id not in ids_for_bulk

    ids_for_sweep = await repo.list_ids_needing_asus_price_refresh(
        stale_before=datetime.now(UTC), limit=10
    )
    assert laptop.id in ids_for_sweep
    assert accessory.id not in ids_for_sweep


@pytest.mark.asyncio
async def test_bulk_run_tracks_live_progress_and_completion(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves the "Update prices" button's progress is real server state,
    not a one-shot message — total/in_progress/completed update as jobs
    finish, and `finished_at` only gets set once every job is truly done."""
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    model_a = await _make_model(db_session, brand.id, "ASUS-BULK-A")
    model_b = await _make_model(db_session, brand.id, "ASUS-BULK-B")
    await _add_available_unit(db_session, model_a.id)
    await _add_available_unit(db_session, model_b.id)

    release = asyncio.Event()

    async def blocked_refresh(session, model_id):
        await release.wait()
        return "ok"

    monkeypatch.setattr(asus_jobs_module, "refresh_asus_live_price", blocked_refresh)

    scheduled = await schedule_all_asus_price_refreshes()
    assert scheduled == 2

    await asyncio.sleep(0.05)
    mid_status = get_asus_bulk_run_status()
    assert mid_status["total"] == 2
    assert mid_status["in_progress"] == 2
    assert mid_status["completed"] == 0
    assert mid_status["started_at"] is not None
    assert mid_status["finished_at"] is None

    release.set()
    await asyncio.sleep(0.05)
    final_status = get_asus_bulk_run_status()
    assert final_status["total"] == 2
    assert final_status["in_progress"] == 0
    assert final_status["completed"] == 2
    assert final_status["finished_at"] is not None
    assert final_status["failed_model_ids"] == []


@pytest.mark.asyncio
async def test_bulk_run_lists_failed_model_ids_for_retry(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that comes back "not_found" (or any non-"ok" outcome) must be
    listed in `failed_model_ids` once the run finishes, so the UI can offer
    a "Retry failed" action scoped to just those models."""
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    good = await _make_model(db_session, brand.id, "ASUS-GOOD")
    bad = await _make_model(db_session, brand.id, "ASUS-BAD")
    await _add_available_unit(db_session, good.id)
    await _add_available_unit(db_session, bad.id)

    async def fake_refresh(session, model_id):
        return "ok" if model_id == good.id else "not_found"

    monkeypatch.setattr(asus_jobs_module, "refresh_asus_live_price", fake_refresh)

    scheduled = await schedule_all_asus_price_refreshes()
    assert scheduled == 2
    await asyncio.sleep(0.05)

    status = get_asus_bulk_run_status()
    assert status["finished_at"] is not None
    assert status["failed_model_ids"] == [str(bad.id)]


@pytest.mark.asyncio
async def test_retry_failed_reschedules_only_the_failed_models(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    good = await _make_model(db_session, brand.id, "ASUS-RETRY-GOOD")
    bad = await _make_model(db_session, brand.id, "ASUS-RETRY-BAD")
    await _add_available_unit(db_session, good.id)
    await _add_available_unit(db_session, bad.id)

    calls: list[uuid.UUID] = []

    async def fake_refresh(session, model_id):
        calls.append(model_id)
        return "ok" if model_id == good.id else "not_found"

    monkeypatch.setattr(asus_jobs_module, "refresh_asus_live_price", fake_refresh)

    await schedule_all_asus_price_refreshes()
    await asyncio.sleep(0.05)
    assert set(calls) == {good.id, bad.id}

    retried = await retry_failed_asus_price_refreshes()
    assert retried == 1
    await asyncio.sleep(0.05)

    # Only the failed model was retried — the already-good one wasn't touched.
    assert calls == [good.id, bad.id, bad.id]
    retry_status = get_asus_bulk_run_status()
    assert retry_status["total"] == 1


@pytest.mark.asyncio
async def test_retry_failed_with_nothing_failed_returns_zero(
    db_session: AsyncSession, test_settings, brand, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    model = await _make_model(db_session, brand.id, "ASUS-ALL-GOOD")
    await _add_available_unit(db_session, model.id)

    async def fake_refresh(session, model_id):
        return "ok"

    monkeypatch.setattr(asus_jobs_module, "refresh_asus_live_price", fake_refresh)
    await schedule_all_asus_price_refreshes()
    await asyncio.sleep(0.05)

    assert await retry_failed_asus_price_refreshes() == 0


@pytest.mark.asyncio
async def test_retry_failed_with_no_prior_run_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    assert await retry_failed_asus_price_refreshes() == 0


@pytest.mark.asyncio
async def test_refresh_status_endpoint_reports_zero_when_idle(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lets the "Update prices" button poll for real completion."""
    monkeypatch.setattr(asus_jobs_module, "_bulk_run", None)
    response = await api_client.get(
        "/api/v1/product-models/refresh-live-prices/status", headers=main_admin_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["in_progress"] == 0
    assert response.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_refresh_status_route_does_not_shadow_get_by_id(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    db_session: AsyncSession,
    brand,
) -> None:
    """Regression guard: the new static `/refresh-live-prices/status` route
    must be registered ahead of `/{model_id}` so it isn't captured as a
    model_id lookup — and `/{model_id}` must keep working normally too."""
    model = await _make_model(db_session, brand.id, "ASUS-007")

    status_response = await api_client.get(
        "/api/v1/product-models/refresh-live-prices/status", headers=main_admin_headers
    )
    assert status_response.status_code == 200

    by_id_response = await api_client.get(
        f"/api/v1/product-models/{model.id}", headers=main_admin_headers
    )
    assert by_id_response.status_code == 200
    assert by_id_response.json()["data"]["model_number"] == "ASUS-007"
