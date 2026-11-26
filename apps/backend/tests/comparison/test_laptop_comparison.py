"""Laptop comparison permission, exact variant, stock and cache regression tests."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.api.schemas.comparison import ExternalLaptopRequest
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    InventoryStatus,
    LocationType,
    ProductCategory,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.laptop_comparison_cache import (
    LaptopComparisonCache,
)
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.session import get_session_factory
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
)
from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.types import AIProviderConfig, ProviderCredentials
from webstudio_backend.services.laptop_comparison import (
    CACHE_LIFETIME,
    UNVERIFIED_MODEL,
    _verified_payload,
    purge_expired_research,
    research_external,
)

pytest_plugins = ["auth.conftest"]
EXTERNAL = "/api/v1/comparison/external"
STOCK = "/api/v1/comparison/inventory"
RAM = "16 GB DDR5 4800 MHz, dual channel, two replaceable modules; maximum supported capacity is 64 GB."


def grounded_fixture(brand: str, sku: str):
    evidence = f"The manufacturer's published configuration identifies {brand} {sku}."
    return (
        {
            "verified": True,
            "brand": brand,
            "model_number": sku,
            "model_name": "Verified product",
            "evidence": evidence,
            "specifications": {
                "Processor": "Intel Core i5-1335U, 10 cores, 12 threads, up to 4.60 GHz, 12 MB cache",
                "RAM": RAM,
                "Additional sensor": "Factory ambient light sensor",
            },
        },
        {
            "candidates": [
                {
                    "groundingMetadata": {
                        "groundingChunks": [
                            {
                                "web": {
                                    "uri": "https://www.lenovo.com/specs",
                                    "title": f"{brand} {sku}",
                                }
                            }
                        ],
                        "groundingSupports": [
                            {"segment": {"text": evidence}, "groundingChunkIndices": [0]}
                        ],
                    },
                }
            ],
        },
    )


@pytest.mark.asyncio
async def test_inventory_comparison_reads_stored_models_without_research(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    initialized_system,
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    def unexpected(*args, **kwargs):
        raise AssertionError("Stock comparison must not invoke Gemini or HTTP research")

    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    monkeypatch.setattr(GeminiProvider, "research_laptop_comparison", unexpected)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unexpected)
    monkeypatch.setattr(test_settings, "webstudio_data_root", str(tmp_path))
    photo = tmp_path / "assets" / "product-images" / "comparison-dell.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"saved-comparison-image")

    brands = [
        await BrandRepository(db_session).create(name)
        for name in ("Comparison Dell", "Comparison Lenovo")
    ]
    location = await LocationRepository(db_session).create(
        "Comparison store", location_type=LocationType.WAREHOUSE
    )
    models = ProductModelRepository(db_session)
    stock = InventoryItemRepository(db_session)
    saved_laptop_configuration = {
        "cpu": "Intel Core i5-1335U",
        "ram_gb": 16,
        "storage_value": Decimal("512"),
        "storage_unit": StorageUnit.GB,
        "storage_type": StorageType.SSD,
    }
    for index, brand in enumerate(brands):
        model = await models.create(
            brand_id=brand.id,
            model_number=f"COMPARE-14-{index}",
            model_name=f"Store laptop {index}",
            notes="Memory type: " + RAM + "\nWarranty: 2 years",
            product_image_url="/assets/product-images/comparison-dell.png" if index == 0 else None,
            **saved_laptop_configuration,
        )
        await stock.create(
            serial_number=f"comparison-case-{index}",
            product_model_id=model.id,
            color="Black",
            current_location_id=location.id,
            status=InventoryStatus.AVAILABLE,
        )
    await models.create(
        brand_id=brands[0].id,
        model_number="COMPARE-14-empty",
        model_name="No stock",
        **saved_laptop_configuration,
    )
    accessory = await models.create(
        brand_id=brands[0].id,
        model_number="COMPARE-14-case",
        model_name="Case",
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.BAG,
    )
    await stock.create(
        serial_number="comparison-accessory",
        product_model_id=accessory.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    models_before = await db_session.scalar(select(func.count()).select_from(ProductModel))

    for search, expected in [
        ("Dell", "COMPARE-14-0"),
        ("14-1", "COMPARE-14-1"),
        ("Lenovo laptop 1", "COMPARE-14-1"),
    ]:
        result = await api_client.get(
            STOCK,
            params={"search": search + " Compare" if search == "Dell" else search},
            headers=headers,
        )
        assert result.status_code == 200
        assert result.json()["data"][0]["model_number"] == expected

    result = await api_client.get(
        STOCK, params={"search": "COMPARE-14-", "page_size": 1, "page": 2}, headers=headers
    )
    assert result.status_code == 200
    assert result.json()["meta"]["total_items"] == 2
    laptop = result.json()["data"][0]
    assert laptop["model_number"] == "COMPARE-14-1"
    assert laptop["available_units"] == 1
    assert laptop["saved_notes"] == "Memory type: " + RAM + "\nWarranty: 2 years"
    assert {"component": "Processor", "detail": "Intel Core i5-1335U"} in laptop["specifications"]
    assert all(item["component"] != "Graphics" for item in laptop["specifications"])
    assert "purchase_price" not in laptop
    assert await db_session.scalar(select(func.count()).select_from(ProductModel)) == models_before
    image = await api_client.get(f"{STOCK}/{laptop['model_id']}/image", headers=headers)
    assert image.status_code == 404
    saved_photo = await api_client.get(STOCK, params={"search": "COMPARE-14-0"}, headers=headers)
    photo_laptop = saved_photo.json()["data"][0]
    assert photo_laptop["managed_image"] is True
    image = await api_client.get(f"{STOCK}/{photo_laptop['model_id']}/image", headers=headers)
    assert image.status_code == 200
    assert image.content == photo.read_bytes()


@pytest.mark.asyncio
async def test_gemini_lookup_requests_grounding_and_rejects_ungrounded_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookup = ExternalLaptopRequest(brand="Lenovo", model_number="21M7ABCD")
    raw, body = grounded_fixture(lookup.brand, lookup.model_number)
    raw["image_url"] = "https://[invalid"
    body["candidates"][0]["content"] = {"parts": [{"text": json.dumps(raw)}]}

    async def generate(self, model, payload):
        assert model == "gemini-fixture"
        assert payload["tools"] == [{"google_search": {}}]
        prompt = payload["contents"][0]["parts"][0]["text"]
        assert lookup.model_number in prompt and lookup.brand in prompt
        assert "upgradeability" in prompt and "regional SKU" in prompt
        return body

    monkeypatch.setattr(GeminiProvider, "_generate", generate)
    provider = GeminiProvider(
        AIProviderConfig(gemini=ProviderCredentials("gemini", "fixture-key", "gemini-fixture"))
    )
    output = await provider.research_laptop_comparison(lookup.brand, lookup.model_number)
    assert output is not None
    laptop = _verified_payload(lookup, *output)
    assert laptop is not None
    assert laptop.image_url is None
    assert any(spec.detail == RAM for spec in laptop.specifications)
    body["candidates"][0].pop("groundingMetadata")
    assert _verified_payload(lookup, *output) is None


@pytest.mark.asyncio
async def test_external_lookup_rejects_ambiguous_results_and_caches_a_verified_retry(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    initialized_system,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def research(self, brand, sku):
        nonlocal calls
        calls += 1
        payload, proof = grounded_fixture(brand, sku)
        if calls == 1:
            payload["model_number"] = sku + "-different"
        return payload, proof

    monkeypatch.setattr(GeminiProvider, "research_laptop_comparison", research)
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    models_before = await db_session.scalar(select(func.count()).select_from(ProductModel))
    sku = "COMPARE-EXACT-" + uuid4().hex[:8].upper()
    body = {"brand": "Lenovo", "model_number": sku}
    unauthorized = await api_client.post(EXTERNAL, json=body)
    assert unauthorized.status_code == 401
    invalid = await api_client.post(
        EXTERNAL, json={"brand": "Lenovo", "model_number": "  "}, headers=headers
    )
    assert invalid.status_code == 422
    assert calls == 0
    failure = await api_client.post(EXTERNAL, json=body, headers=headers)
    assert failure.status_code == 404
    assert UNVERIFIED_MODEL in failure.text
    key = ("lenovo", sku.lower())
    assert await db_session.get(LaptopComparisonCache, key) is None

    verified = await api_client.post(EXTERNAL, json=body, headers=headers)
    assert verified.status_code == 200
    laptop = verified.json()["data"]
    assert laptop["source"] == "external"
    assert laptop["available_units"] is None and laptop["selling_price"] is None
    assert {"component": "RAM", "detail": RAM} in laptop["specifications"]
    assert {"component": "Additional sensor", "detail": "Factory ambient light sensor"} in laptop[
        "specifications"
    ]
    stored = await db_session.get(LaptopComparisonCache, key)
    assert stored is not None and stored.expires_at - stored.created_at == CACHE_LIFETIME

    cached = await api_client.post(
        EXTERNAL, json={"brand": " lenovo ", "model_number": sku.lower()}, headers=headers
    )
    assert cached.status_code == 200
    assert cached.json()["data"] == laptop
    assert calls == 2
    assert await db_session.scalar(select(func.count()).select_from(ProductModel)) == models_before


@pytest.mark.asyncio
async def test_cache_persists_coalesces_concurrent_request_and_refreshes_after_expiry(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def research(self, brand, sku):
        calls.append(sku)
        await asyncio.sleep(0.04)
        return grounded_fixture(brand, sku)

    monkeypatch.setattr(GeminiProvider, "research_laptop_comparison", research)
    prefix = "COMPARE-PERSIST-" + uuid4().hex[:8].upper()
    sku_a, sku_b = f"{prefix}-A", f"{prefix}-B"
    lookup = ExternalLaptopRequest(brand="Lenovo", model_number=sku_a)
    factory = get_session_factory()

    async def lookup_on_new_session(request: ExternalLaptopRequest):
        async with factory() as session:
            result = await research_external(session, test_settings, request)
            await session.commit()
            return result

    first, second = await asyncio.gather(
        lookup_on_new_session(lookup), lookup_on_new_session(lookup)
    )
    assert first == second
    assert await lookup_on_new_session(lookup) == first
    assert calls == [sku_a]
    variant = ExternalLaptopRequest(brand="Lenovo", model_number=sku_b)
    assert (await lookup_on_new_session(variant)).model_number == sku_b
    assert len(calls) == 2

    expired = datetime.now(UTC) - timedelta(seconds=1)
    filter_a = LaptopComparisonCache.normalized_model == sku_a.lower()
    filter_b = LaptopComparisonCache.normalized_model == sku_b.lower()
    await db_session.execute(
        update(LaptopComparisonCache).where(filter_a | filter_b).values(expires_at=expired)
    )
    await db_session.commit()
    await lookup_on_new_session(lookup)
    assert calls == [sku_a, sku_b, sku_a]
    await purge_expired_research(db_session)
    await db_session.commit()
    assert await db_session.scalar(select(LaptopComparisonCache).where(filter_b)) is None
    assert await db_session.scalar(select(LaptopComparisonCache).where(filter_a)) is not None
    await db_session.execute(
        update(LaptopComparisonCache).where(filter_a).values(payload={"source": "external"})
    )
    await db_session.commit()
    assert (await lookup_on_new_session(lookup)).model_number == sku_a
    assert calls == [sku_a, sku_b, sku_a, sku_a]
