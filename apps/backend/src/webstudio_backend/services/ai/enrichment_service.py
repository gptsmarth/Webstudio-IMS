"""Product enrichment orchestrator with provider fallback."""

from __future__ import annotations

import time
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.services.ai.cache import EnrichmentCacheService
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.providers.factory import build_provider_chain, create_provider
from webstudio_backend.services.ai.types import AIProviderError, EnrichmentResult, ProviderId, ProviderTestResult
from webstudio_backend.services.product_image_service import resolve_product_image


class ProductEnrichmentService:
    """Server-side product enrichment with caching and provider fallback."""

    def __init__(self, session: AsyncSession, app_settings: Settings) -> None:
        self._session = session
        self._app_settings = app_settings

    async def lookup_laptop_spec(
        self,
        model_number: str,
        *,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> dict[str, Any]:
        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.")

        config = await resolve_ai_config(self._session, self._app_settings)
        if not config.enrichment_enabled:
            raise AIProviderError(
                "SERVICE_UNAVAILABLE",
                "AI product enrichment is disabled in System Settings → Integrations.",
            )

        cache = EnrichmentCacheService(self._session)
        cached = await cache.get(sku, brand_name=brand_name)
        if cached and cached.get("cpu"):
            from webstudio_backend.services.ai.spec_normalization import validate_enrichment_payload

            provider = str(cached.get("provider") or "gemini")
            if validate_enrichment_payload(
                cached,
                model_number=sku,
                provider=provider,
                brand_name=brand_name,
            ):
                logger.info("Enrichment cache hit for {}", sku)
                cached["cached"] = True
                return cached
            logger.info("Stale enrichment cache rejected for {}, refreshing", sku)
            await cache.delete(sku, brand_name=brand_name)

        existing = await self._lookup_existing_model(sku, brand_name=brand_name)
        if existing:
            logger.info("Reusing existing product model enrichment for {}", sku)
            existing["cached"] = True
            await cache.set(
                sku,
                brand_name=brand_name,
                payload=existing,
                provider=str(existing.get("provider") or "database"),
            )
            return existing

        chain = build_provider_chain(config)
        configured_chain = [provider for provider in chain if provider.is_configured() or provider.provider_id == "mock"]
        if not configured_chain:
            raise AIProviderError(
                "NOT_CONFIGURED",
                "No AI provider is configured. Add an API key in System Settings → Integrations.",
            )

        errors: list[AIProviderError] = []
        for provider in configured_chain:
            started = time.perf_counter()
            try:
                result = await provider.enrich_product_spec(
                    sku,
                    brand_name=brand_name,
                    model_name=model_name,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "Enrichment succeeded via {} for {} in {}ms (confidence={:.2f})",
                    provider.provider_id,
                    sku,
                    duration_ms,
                    result.confidence_score,
                )
                finalized = await self._finalize_result(
                    result,
                    model_number=sku,
                    brand_name=brand_name,
                )
                await cache.set(
                    sku,
                    brand_name=brand_name,
                    payload=finalized,
                    provider=provider.provider_id,
                )
                return finalized
            except AIProviderError as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "Enrichment failed via {} for {} after {}ms: {}",
                    provider.provider_id,
                    sku,
                    duration_ms,
                    exc.message,
                )
                errors.append(exc)
                if exc.code in {"RATE_LIMITED", "TIMEOUT", "QUOTA_EXCEEDED", "API_ERROR", "NOT_FOUND"}:
                    continue
                raise

        if errors:
            raise self._combine_errors(errors)
        raise AIProviderError(
            "NOT_FOUND",
            "Could not resolve laptop specifications. Enter details manually.",
        )

    async def test_provider(self, provider_id: ProviderId) -> ProviderTestResult:
        config = await resolve_ai_config(self._session, self._app_settings)
        provider = create_provider(provider_id, config)
        return await provider.test_connection()

    async def _lookup_existing_model(
        self,
        model_number: str,
        *,
        brand_name: str | None,
    ) -> dict[str, Any] | None:
        statement = select(ProductModel, Brand.name).join(Brand, Brand.id == ProductModel.brand_id)
        statement = statement.where(ProductModel.model_number.ilike(model_number.strip()))
        if brand_name:
            statement = statement.where(Brand.name.ilike(brand_name.strip()))
        row = (await self._session.execute(statement.limit(1))).first()
        if row is None:
            return None
        product_model, resolved_brand = row
        if not product_model.cpu:
            return None
        return {
            "model_name": product_model.model_name,
            "cpu": product_model.cpu,
            "gpu": product_model.gpu,
            "ram_gb": product_model.ram_gb,
            "storage_value": str(product_model.storage_value),
            "storage_unit": product_model.storage_unit.value,
            "storage_type": product_model.storage_type.value,
            "display": product_model.display,
            "color_options": product_model.color_options,
            "product_image_url": product_model.product_image_url,
            "description": None,
            "notes": product_model.notes,
            "source": "database",
            "provider": "database",
            "confidence_score": 1.0,
            "cached": True,
        }

    async def _finalize_result(
        self,
        result: EnrichmentResult,
        *,
        model_number: str,
        brand_name: str | None,
    ) -> dict[str, Any]:
        payload = result.to_dict()
        image_url = await resolve_product_image(
            model_number=model_number,
            brand_name=brand_name,
            model_name=result.model_name,
            candidate_url=result.product_image_url,
            grounding_body=result.grounding_body,
            image_search_query=result.image_search_query,
        )
        payload["product_image_url"] = image_url
        payload["source"] = result.source
        payload["provider"] = result.provider
        return payload

    @staticmethod
    def _combine_errors(errors: list[AIProviderError]) -> AIProviderError:
        if any(error.code == "RATE_LIMITED" for error in errors):
            return AIProviderError(
                "RATE_LIMITED",
                "All configured AI providers are rate-limited. Wait a few minutes or enter specifications manually.",
            )
        if any(error.code == "QUOTA_EXCEEDED" for error in errors):
            return AIProviderError(
                "QUOTA_EXCEEDED",
                "All configured AI providers exceeded their quota. Enter specifications manually.",
            )
        if any(error.code == "TIMEOUT" for error in errors):
            return AIProviderError(
                "TIMEOUT",
                "AI enrichment timed out across all configured providers.",
            )
        last = errors[-1]
        return AIProviderError(
            last.code,
            last.message or "Could not resolve laptop specifications. Enter details manually.",
        )
