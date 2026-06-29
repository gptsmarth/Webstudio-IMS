"""Deterministic mock AI provider for tests."""

from __future__ import annotations

import hashlib
import time

from webstudio_backend.services.ai.prompts import default_image_search_query
from webstudio_backend.services.ai.providers.base import AIProvider
from webstudio_backend.services.ai.types import AIProviderConfig, EnrichmentResult, ProviderTestResult


class MockProvider(AIProvider):
    provider_id = "mock"

    def __init__(self, config: AIProviderConfig) -> None:
        super().__init__(config)

    def is_configured(self) -> bool:
        return True

    async def enrich_product_spec(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> EnrichmentResult:
        sku = model_number.strip().upper()
        digest = hashlib.sha256(sku.encode()).hexdigest()
        ram_options = (8, 16, 32)
        storage_options = ("256", "512", "1024")
        ram_gb = ram_options[int(digest[:2], 16) % len(ram_options)]
        storage_value = storage_options[int(digest[2:4], 16) % len(storage_options)]
        resolved_name = model_name or f"Mock Laptop {sku.split('-', 1)[0]}"
        brand_prefix = f"{brand_name} " if brand_name else ""
        return EnrichmentResult(
            model_name=resolved_name,
            cpu="Intel Core i5-1335U",
            gpu="Intel UHD Graphics",
            ram_gb=ram_gb,
            storage_value=storage_value,
            storage_unit="GB",
            storage_type="SSD",
            display='15.6" FHD IPS 60Hz',
            color_options="Quiet Blue",
            product_image_url=None,
            description=f"{brand_prefix}{resolved_name} is a mock enrichment result for automated testing.",
            notes=f"Mock provider enrichment for {sku}.",
            source="mock",
            provider="mock",
            confidence_score=1.0,
            image_search_query=default_image_search_query(
                sku,
                brand_name=brand_name,
                model_name=resolved_name,
            ),
        )

    async def generate_image_search_query(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> str:
        return default_image_search_query(model_number, brand_name=brand_name, model_name=model_name)

    async def test_connection(self) -> ProviderTestResult:
        started = time.perf_counter()
        await self.enrich_product_spec("MOCK-TEST-001", brand_name="ASUS")
        latency = int((time.perf_counter() - started) * 1000)
        return ProviderTestResult(
            provider="mock",
            success=True,
            message="Mock provider is available.",
            latency_ms=latency,
        )
