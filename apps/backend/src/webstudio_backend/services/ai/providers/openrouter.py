"""OpenRouter AI provider (OpenAI-compatible API)."""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from webstudio_backend.services.ai.health import AIProviderHealthTracker
from webstudio_backend.services.ai.json_utils import parse_json_object
from webstudio_backend.services.ai.prompts import (
    build_image_search_query_prompt,
    build_spec_lookup_prompt,
    default_image_search_query,
)
from webstudio_backend.services.ai.providers.base import AIProvider
from webstudio_backend.services.ai.spec_normalization import (
    normalize_spec,
    validate_enrichment_payload,
)
from webstudio_backend.services.ai.types import (
    AIProviderConfig,
    AIProviderError,
    EnrichmentResult,
    ProviderTestResult,
)

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(AIProvider):
    provider_id = "openrouter"

    def __init__(self, config: AIProviderConfig) -> None:
        super().__init__(config)
        self._api_key = config.openrouter.api_key.strip()
        self._model = config.openrouter.model.strip() or DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def enrich_product_spec(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> EnrichmentResult:
        if not self.is_configured():
            raise AIProviderError(
                "NOT_CONFIGURED",
                "OpenRouter API is not configured.",
                provider="openrouter",
            )

        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.", provider="openrouter")

        prompt = build_spec_lookup_prompt(
            sku, brand_name=brand_name, model_name=model_name, use_web_search=False
        )
        started = time.perf_counter()
        AIProviderHealthTracker.record_request("openrouter")
        try:
            body = await self._chat(prompt, json_mode=True)
            parsed_raw = parse_json_object(_extract_chat_text(body) or "")
            if not parsed_raw:
                raise AIProviderError(
                    "NOT_FOUND",
                    "OpenRouter returned an unreadable response.",
                    provider="openrouter",
                )
            normalized = normalize_spec(
                parsed_raw, fallback_name=model_name or sku, source="openrouter"
            )
            if not validate_enrichment_payload(
                normalized,
                model_number=sku,
                provider="openrouter",
                brand_name=brand_name,
            ):
                raise AIProviderError(
                    "NOT_FOUND",
                    "OpenRouter could not produce validated specifications for this SKU.",
                    provider="openrouter",
                )
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info("OpenRouter enrichment succeeded for {} in {}ms", sku, duration_ms)
            AIProviderHealthTracker.record_success("openrouter")
            image_query = await self.generate_image_search_query(
                sku,
                brand_name=brand_name,
                model_name=normalized.get("model_name") or model_name,
            )
            return EnrichmentResult(
                model_name=normalized["model_name"],
                cpu=normalized["cpu"],
                gpu=normalized.get("gpu"),
                ram_gb=int(normalized["ram_gb"]),
                storage_value=normalized["storage_value"],
                storage_unit=normalized["storage_unit"],
                storage_type=normalized["storage_type"],
                display=normalized.get("display"),
                color_options=normalized.get("color_options"),
                product_image_url=None,
                description=normalized.get("description"),
                notes=normalized.get("notes"),
                source="openrouter",
                provider="openrouter",
                confidence_score=float(normalized.get("confidence_score") or 0.6),
                image_search_query=image_query,
            )
        except AIProviderError as exc:
            if exc.code == "RATE_LIMITED":
                AIProviderHealthTracker.record_rate_limit("openrouter", message=exc.message)
            elif exc.code == "QUOTA_EXCEEDED":
                AIProviderHealthTracker.record_quota_exceeded("openrouter", message=exc.message)
            else:
                AIProviderHealthTracker.record_failure("openrouter", message=exc.message)
            raise

    async def generate_image_search_query(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> str:
        fallback = default_image_search_query(
            model_number, brand_name=brand_name, model_name=model_name
        )
        if not self.is_configured():
            return fallback
        prompt = build_image_search_query_prompt(
            model_number, brand_name=brand_name, model_name=model_name
        )
        try:
            body = await self._chat(prompt, json_mode=True)
            parsed = parse_json_object(_extract_chat_text(body) or "")
            if parsed and isinstance(parsed.get("image_search_query"), str):
                query = parsed["image_search_query"].strip()
                if query:
                    return query[:256]
        except AIProviderError:
            pass
        return fallback

    async def test_connection(self) -> ProviderTestResult:
        if not self.is_configured():
            return ProviderTestResult(
                provider="openrouter",
                success=False,
                message="OpenRouter API key is not configured.",
            )
        started = time.perf_counter()
        try:
            await self._chat('Respond with JSON: {"status":"ok"}', json_mode=True)
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                provider="openrouter",
                success=True,
                message=f"Connected to OpenRouter model {self._model}.",
                latency_ms=latency,
            )
        except AIProviderError as exc:
            return ProviderTestResult(provider="openrouter", success=False, message=exc.message)

    async def _chat(self, prompt: str, *, json_mode: bool) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://webstudio.local",
            "X-Title": "WEBSTUDIO IMS",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                response = await client.post(API_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "TIMEOUT", "OpenRouter request timed out.", provider="openrouter"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                "API_ERROR", "Could not reach OpenRouter.", provider="openrouter"
            ) from exc

        if response.status_code == 429:
            raise AIProviderError(
                "RATE_LIMITED", "OpenRouter rate limit reached.", provider="openrouter"
            )
        if response.status_code in {401, 403}:
            raise AIProviderError(
                "API_ERROR", "OpenRouter API key was rejected.", provider="openrouter"
            )
        if response.status_code == 402:
            raise AIProviderError(
                "QUOTA_EXCEEDED", "OpenRouter quota exceeded.", provider="openrouter"
            )
        if response.status_code >= 400:
            raise AIProviderError("API_ERROR", "OpenRouter request failed.", provider="openrouter")
        return response.json()


def _extract_chat_text(body: dict[str, Any]) -> str | None:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) else None
