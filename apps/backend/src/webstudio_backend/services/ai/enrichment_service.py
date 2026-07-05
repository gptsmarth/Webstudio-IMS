"""Product enrichment orchestrator — multi-provider spec lookup with fallback."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ProductCategory
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.services.ai.cache import EnrichmentCacheService
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.logging import (
    log_cache_hit,
    log_cache_stale,
    log_database_reuse,
    log_enrichment_retry,
    log_enrichment_start,
    log_provider_attempt,
    log_provider_failure,
    log_provider_success,
    log_provider_test,
)
from webstudio_backend.services.ai.providers.factory import build_provider_chain, create_provider
from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.types import (
    AIProviderError,
    EnrichmentResult,
    ProviderId,
    ProviderTestResult,
)
from webstudio_backend.services.product_image_service import resolve_product_image

_inflight_spec_lookups: dict[str, asyncio.Task[dict[str, Any]]] = {}
_inflight_accessory_lookups: dict[str, asyncio.Task[dict[str, Any]]] = {}


def _spec_lookup_providers(config, app_settings: Settings):
    """Return configured providers in fallback order."""
    chain = build_provider_chain(config)
    configured = [provider for provider in chain if provider.is_configured()]
    if app_settings.is_test:
        configured = [
            provider
            for provider in chain
            if provider.is_configured() or provider.provider_id == "mock"
        ]
    return configured


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

        inflight_key = f"{sku.lower()}|{(brand_name or '').strip().lower()}"
        existing_task = _inflight_spec_lookups.get(inflight_key)
        if existing_task is not None:
            return await asyncio.shield(existing_task)

        task = asyncio.create_task(
            self._lookup_laptop_spec_impl(
                sku,
                model_name=model_name,
                brand_name=brand_name,
            )
        )
        _inflight_spec_lookups[inflight_key] = task
        try:
            return await task
        finally:
            if _inflight_spec_lookups.get(inflight_key) is task:
                _inflight_spec_lookups.pop(inflight_key, None)

    async def _lookup_laptop_spec_impl(
        self,
        sku: str,
        *,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> dict[str, Any]:
        config = await resolve_ai_config(self._session, self._app_settings)
        if not config.enrichment_enabled:
            raise AIProviderError(
                "SERVICE_UNAVAILABLE",
                "AI product enrichment is disabled in System Settings → Integrations.",
            )

        configured_chain = _spec_lookup_providers(config, self._app_settings)
        if not configured_chain and not self._app_settings.is_test:
            raise AIProviderError(
                "NOT_CONFIGURED",
                "No AI provider is configured. Add a Gemini API key in System Settings → Integrations.",
            )

        cache = EnrichmentCacheService(self._session)
        cached = await cache.get(sku, brand_name=brand_name)
        if cached and cached.get("cpu"):
            from webstudio_backend.services.ai.spec_normalization import validate_enrichment_payload

            provider = str(cached.get("provider") or config.primary_provider)
            if validate_enrichment_payload(
                cached,
                model_number=sku,
                provider=provider,
                brand_name=brand_name,
            ):
                log_cache_hit(sku=sku, provider=provider)
                cached["cached"] = True
                return cached
            log_cache_stale(sku=sku)
            await cache.delete(sku, brand_name=brand_name)

        existing = await self._lookup_existing_model(sku, brand_name=brand_name)
        if existing:
            log_database_reuse(sku=sku)
            existing["cached"] = True
            await cache.set(
                sku,
                brand_name=brand_name,
                payload=existing,
                provider=str(existing.get("provider") or "database"),
            )
            return existing

        if not configured_chain:
            raise AIProviderError(
                "NOT_CONFIGURED",
                "No AI provider is configured. Add a Gemini API key in System Settings → Integrations.",
            )

        retry_attempts = max(1, config.retry_count)
        errors: list[AIProviderError] = []
        provider_ids = [provider.provider_id for provider in configured_chain]
        for attempt in range(retry_attempts):
            if attempt > 0:
                delay = 3.0 * attempt
                log_enrichment_retry(
                    sku=sku,
                    attempt=attempt + 1,
                    max_attempts=retry_attempts,
                    delay_seconds=delay,
                )
                await asyncio.sleep(delay)
            else:
                log_enrichment_start(
                    sku=sku,
                    attempt=1,
                    max_attempts=retry_attempts,
                    providers=provider_ids,
                )
            errors = []
            for provider in configured_chain:
                started = time.perf_counter()
                log_provider_attempt(provider=provider.provider_id, sku=sku, attempt=attempt + 1)
                try:
                    result = await provider.enrich_product_spec(
                        sku,
                        brand_name=brand_name,
                        model_name=model_name,
                    )
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    log_provider_success(
                        provider=provider.provider_id,
                        sku=sku,
                        duration_ms=duration_ms,
                        confidence=result.confidence_score,
                    )
                    spec_payload = result.to_dict()
                    spec_payload["source"] = result.source
                    spec_payload["provider"] = result.provider
                    await cache.set(
                        sku,
                        brand_name=brand_name,
                        payload=spec_payload,
                        provider=provider.provider_id,
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
                    log_provider_failure(
                        provider=provider.provider_id,
                        sku=sku,
                        duration_ms=duration_ms,
                        code=exc.code,
                        message=exc.message,
                    )
                    errors.append(exc)
                    if exc.code in {
                        "RATE_LIMITED",
                        "TIMEOUT",
                        "QUOTA_EXCEEDED",
                        "API_ERROR",
                        "NOT_FOUND",
                    }:
                        continue
                    raise

            if errors and attempt < retry_attempts - 1:
                if any(
                    error.code in {"RATE_LIMITED", "TIMEOUT", "QUOTA_EXCEEDED"} for error in errors
                ):
                    continue

        if errors:
            raise self._combine_errors(errors)
        raise AIProviderError(
            "NOT_FOUND",
            "Could not resolve laptop specifications. Enter details manually.",
        )

    async def lookup_accessory_spec(
        self,
        identifier: str,
        *,
        identifier_type: str = "model_number",
        brand_name: str | None = None,
        accessory_kind: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        sku = identifier.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Part or model number is required.")

        inflight_key = (
            f"accessory:{identifier_type}:{sku.lower()}|{(brand_name or '').strip().lower()}"
        )
        existing_task = _inflight_accessory_lookups.get(inflight_key)
        if existing_task is not None:
            return await asyncio.shield(existing_task)

        task = asyncio.create_task(
            self._lookup_accessory_spec_impl(
                sku,
                identifier_type=identifier_type,
                brand_name=brand_name,
                accessory_kind=accessory_kind,
                model_name=model_name,
            )
        )
        _inflight_accessory_lookups[inflight_key] = task
        try:
            return await task
        finally:
            if _inflight_accessory_lookups.get(inflight_key) is task:
                _inflight_accessory_lookups.pop(inflight_key, None)

    async def _lookup_accessory_spec_impl(
        self,
        sku: str,
        *,
        identifier_type: str,
        brand_name: str | None,
        accessory_kind: str | None,
        model_name: str | None,
    ) -> dict[str, Any]:
        config = await resolve_ai_config(self._session, self._app_settings)
        if not config.enrichment_enabled:
            raise AIProviderError(
                "SERVICE_UNAVAILABLE",
                "AI product enrichment is disabled in System Settings → Integrations.",
            )

        cache = EnrichmentCacheService(self._session)
        cache_key = f"accessory:{identifier_type}:{sku}"
        cached = await cache.get(cache_key, brand_name=brand_name)
        if cached and cached.get("model_name"):
            log_cache_hit(sku=sku, provider=str(cached.get("provider") or "cache"))
            cached["cached"] = True
            return cached

        existing = await self._lookup_existing_accessory(
            sku,
            brand_name=brand_name,
            identifier_type=identifier_type,
        )
        if existing:
            log_database_reuse(sku=sku)
            existing["cached"] = True
            await cache.set(
                cache_key,
                brand_name=brand_name,
                payload=existing,
                provider="database",
            )
            return existing

        provider = create_provider("gemini", config)
        if not isinstance(provider, GeminiProvider) or not provider.is_configured():
            if self._app_settings.is_test:
                provider = create_provider("mock", config)
            else:
                raise AIProviderError(
                    "NOT_CONFIGURED",
                    "No AI provider is configured. Add a Gemini API key in System Settings → Integrations.",
                )

        started = time.perf_counter()
        log_enrichment_start(sku=sku, attempt=1, max_attempts=1, providers=["gemini"])
        log_provider_attempt(provider="gemini", sku=sku, attempt=1)
        try:
            if isinstance(provider, GeminiProvider):
                result = await provider.enrich_accessory_spec(
                    sku,
                    identifier_type=identifier_type,
                    brand_name=brand_name,
                    accessory_kind=accessory_kind,
                    model_name=model_name,
                )
            else:
                raise AIProviderError("NOT_CONFIGURED", "Accessory lookup requires Gemini.")
        except AIProviderError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_provider_failure(
                provider="gemini",
                sku=sku,
                duration_ms=duration_ms,
                code=exc.code,
                message=exc.message,
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        log_provider_success(
            provider="gemini",
            sku=sku,
            duration_ms=duration_ms,
            confidence=float(result.get("confidence_score") or 0.85),
        )
        spec_payload = self._accessory_spec_cache_payload(result)
        await cache.set(
            cache_key,
            brand_name=brand_name,
            payload=spec_payload,
            provider="gemini",
        )
        finalized = await self._finalize_accessory_result(
            result,
            identifier=sku,
            brand_name=brand_name,
        )
        await cache.set(
            cache_key,
            brand_name=brand_name,
            payload=finalized,
            provider="gemini",
        )
        return finalized

    async def test_provider(self, provider_id: ProviderId) -> ProviderTestResult:
        config = await resolve_ai_config(self._session, self._app_settings)
        provider = create_provider(provider_id, config)
        result = await provider.test_connection()
        log_provider_test(
            provider=result.provider,
            success=result.success,
            latency_ms=result.latency_ms,
            message=result.message,
        )
        return result

    async def _lookup_existing_accessory(
        self,
        identifier: str,
        *,
        brand_name: str | None,
        identifier_type: str,
    ) -> dict[str, Any] | None:
        from sqlalchemy import or_

        statement = select(ProductModel, Brand.name).join(Brand, Brand.id == ProductModel.brand_id)
        statement = statement.where(ProductModel.category == ProductCategory.ACCESSORY)
        normalized = identifier.strip()
        if identifier_type == "part_number":
            statement = statement.where(
                or_(
                    ProductModel.part_number.ilike(normalized),
                    ProductModel.model_number.ilike(normalized),
                )
            )
        else:
            statement = statement.where(
                or_(
                    ProductModel.model_number.ilike(normalized),
                    ProductModel.part_number.ilike(normalized),
                )
            )
        if brand_name:
            statement = statement.where(Brand.name.ilike(brand_name.strip()))
        row = (await self._session.execute(statement.limit(1))).first()
        if row is None:
            return None
        product_model, _resolved_brand = row
        return {
            "model_name": product_model.model_name,
            "model_number": product_model.model_number,
            "part_number": product_model.part_number,
            "accessory_kind": (
                product_model.accessory_kind.value if product_model.accessory_kind else None
            ),
            "color_options": product_model.color_options,
            "product_image_url": product_model.product_image_url,
            "description": None,
            "notes": product_model.notes,
            "source": "database",
            "provider": "database",
            "confidence_score": 1.0,
            "cached": True,
        }

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
        if self._app_settings.is_test:
            payload["product_image_url"] = result.product_image_url
        else:
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
    def _accessory_spec_cache_payload(result: dict[str, Any]) -> dict[str, Any]:
        payload = dict(result)
        payload.pop("grounding_body", None)
        payload.pop("image_search_query", None)
        payload.setdefault("product_image_url", None)
        payload["cached"] = False
        return payload

    async def _finalize_accessory_result(
        self,
        result: dict[str, Any],
        *,
        identifier: str,
        brand_name: str | None,
    ) -> dict[str, Any]:
        payload = dict(result)
        if self._app_settings.is_test:
            payload["product_image_url"] = result.get("product_image_url")
        else:
            lookup_number = payload.get("model_number") or payload.get("part_number") or identifier
            try:
                image_url = await asyncio.wait_for(
                    resolve_product_image(
                        model_number=lookup_number,
                        brand_name=brand_name,
                        model_name=result.get("model_name"),
                        candidate_url=result.get("product_image_url"),
                        grounding_body=result.get("grounding_body"),
                        image_search_query=result.get("image_search_query"),
                        fast=True,
                    ),
                    timeout=6.0,
                )
            except asyncio.TimeoutError:
                image_url = None
            payload["product_image_url"] = image_url
        payload.pop("grounding_body", None)
        payload.pop("image_search_query", None)
        payload["cached"] = False
        return payload

    @staticmethod
    def _combine_errors(errors: list[AIProviderError]) -> AIProviderError:
        if any(error.code == "RATE_LIMITED" for error in errors):
            return AIProviderError(
                "RATE_LIMITED",
                "AI providers are rate-limited. Wait a few minutes or enter specifications manually.",
            )
        if any(error.code == "QUOTA_EXCEEDED" for error in errors):
            return AIProviderError(
                "QUOTA_EXCEEDED",
                "AI provider quota exceeded. Check billing or enter specifications manually.",
            )
        if any(error.code == "TIMEOUT" for error in errors):
            return AIProviderError(
                "TIMEOUT",
                "AI enrichment timed out. Try again in a moment.",
            )
        if any(error.code == "API_ERROR" for error in errors):
            return AIProviderError(
                "API_ERROR",
                "AI enrichment failed. Check your API keys in Settings → Integrations.",
            )
        last = errors[-1]
        return AIProviderError(
            last.code,
            last.message or "Could not resolve laptop specifications. Enter details manually.",
        )
