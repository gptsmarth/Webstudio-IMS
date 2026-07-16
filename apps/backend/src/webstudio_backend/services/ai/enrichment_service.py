"""Product enrichment orchestrator — multi-provider spec lookup with fallback."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.services.ai.cache import EnrichmentCacheService
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.logging import (
    log_cache_hit,
    log_cache_stale,
    log_enrichment_retry,
    log_enrichment_start,
    log_provider_attempt,
    log_provider_failure,
    log_provider_success,
    log_provider_test,
)
from webstudio_backend.services.ai.providers.factory import build_provider_chain, create_provider
from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.spec_normalization import validate_enrichment_payload
from webstudio_backend.services.ai.types import (
    AIProviderError,
    EnrichmentResult,
    ProviderId,
    ProviderTestResult,
)

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
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.")

        inflight_key = f"{sku.lower()}|{(brand_name or '').strip().lower()}|refresh={force_refresh}"
        existing_task = _inflight_spec_lookups.get(inflight_key)
        if existing_task is not None:
            return await asyncio.shield(existing_task)

        task = asyncio.create_task(
            self._lookup_laptop_spec_impl(
                sku,
                model_name=model_name,
                brand_name=brand_name,
                force_refresh=force_refresh,
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
        force_refresh: bool = False,
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
        if force_refresh:
            await cache.delete(sku, brand_name=brand_name)
        else:
            cached = await cache.get(sku, brand_name=brand_name)
            if cached and cached.get("cpu"):
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
                    finalized = await self._finalize_result(
                        result,
                        model_number=sku,
                        brand_name=brand_name,
                    )
                    # Single cache write — avoid duplicate token-costly round trips being re-run.
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
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        sku = identifier.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Part or model number is required.")

        inflight_key = (
            f"accessory:{identifier_type}:{sku.lower()}|{(brand_name or '').strip().lower()}"
            f"|refresh={force_refresh}"
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
                force_refresh=force_refresh,
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
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        config = await resolve_ai_config(self._session, self._app_settings)
        if not config.enrichment_enabled:
            raise AIProviderError(
                "SERVICE_UNAVAILABLE",
                "AI product enrichment is disabled in System Settings → Integrations.",
            )

        cache = EnrichmentCacheService(self._session)
        cache_key = f"accessory:{identifier_type}:{sku}"
        if force_refresh:
            await cache.delete(cache_key, brand_name=brand_name)
        else:
            cached = await cache.get(cache_key, brand_name=brand_name)
            if cached and cached.get("model_name"):
                log_cache_hit(sku=sku, provider=str(cached.get("provider") or "cache"))
                cached["cached"] = True
                return cached

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

    async def _finalize_result(
        self,
        result: EnrichmentResult,
        *,
        model_number: str,
        brand_name: str | None,
    ) -> dict[str, Any]:
        payload = result.to_dict()
        # Spec lookup must stay fast and token-cheap — never scrape images here.
        # Background image jobs rebuild a deterministic search query (no AI tokens).
        payload["product_image_url"] = None
        payload.pop("image_search_query", None)
        payload.pop("grounding_body", None)
        payload["source"] = result.source
        payload["provider"] = result.provider
        payload["cached"] = False
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
        del identifier, brand_name
        payload = dict(result)
        # Keep accessory auto-fetch fast — images run after model create (no AI tokens).
        payload["product_image_url"] = None
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
