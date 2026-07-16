"""OpenAI ChatGPT provider (direct OpenAI API)."""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from webstudio_backend.services.ai.health import AIProviderHealthTracker
from webstudio_backend.services.ai.json_utils import parse_json_object
from webstudio_backend.services.ai.prompts import (
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

DEFAULT_MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    provider_id = "openai"

    def __init__(self, config: AIProviderConfig) -> None:
        super().__init__(config)
        self._api_key = config.openai.api_key.strip()
        self._model = config.openai.model.strip() or DEFAULT_MODEL

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
                "OpenAI API is not configured. Add your API key in System Settings → Integrations.",
                provider="openai",
            )

        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.", provider="openai")

        prompt = build_spec_lookup_prompt(
            sku, brand_name=brand_name, model_name=model_name, use_web_search=False
        )
        started = time.perf_counter()
        AIProviderHealthTracker.record_request("openai")

        try:
            body = await self._chat(prompt, json_mode=True)
            parsed_raw = parse_json_object(_extract_chat_text(body) or "")
            if not parsed_raw:
                raise AIProviderError(
                    "NOT_FOUND",
                    "OpenAI returned an unreadable response.",
                    provider="openai",
                )
            normalized = normalize_spec(
                parsed_raw, fallback_name=model_name or sku, source="openai"
            )
            if not validate_enrichment_payload(
                normalized,
                model_number=sku,
                provider="openai",
                brand_name=brand_name,
            ):
                raise AIProviderError(
                    "NOT_FOUND",
                    "OpenAI could not produce validated specifications for this SKU.",
                    provider="openai",
                )
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info("OpenAI enrichment succeeded for {} in {}ms", sku, duration_ms)
            AIProviderHealthTracker.record_success("openai")
            # Deterministic query — never spend an extra AI call just for image search text.
            image_query = default_image_search_query(
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
                source="openai",
                provider="openai",
                confidence_score=float(normalized.get("confidence_score") or 0.65),
                image_search_query=image_query,
            )
        except AIProviderError as exc:
            if exc.code == "RATE_LIMITED":
                AIProviderHealthTracker.record_rate_limit("openai", message=exc.message)
            elif exc.code == "QUOTA_EXCEEDED":
                AIProviderHealthTracker.record_quota_exceeded("openai", message=exc.message)
            else:
                AIProviderHealthTracker.record_failure("openai", message=exc.message)
            raise

    async def generate_image_search_query(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> str:
        return default_image_search_query(
            model_number, brand_name=brand_name, model_name=model_name
        )

    async def test_connection(self) -> ProviderTestResult:
        if not self.is_configured():
            return ProviderTestResult(
                provider="openai",
                success=False,
                message="OpenAI API key is not configured.",
            )
        started = time.perf_counter()
        try:
            await self._chat('Respond with JSON: {"status":"ok"}', json_mode=True)
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                provider="openai",
                success=True,
                message=f"Connected to OpenAI model {self._model}.",
                latency_ms=latency,
            )
        except AIProviderError as exc:
            return ProviderTestResult(provider="openai", success=False, message=exc.message)

    async def _chat(self, prompt: str, *, json_mode: bool) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
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
                "TIMEOUT", "OpenAI request timed out.", provider="openai"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                "API_ERROR", "Could not reach OpenAI.", provider="openai"
            ) from exc

        if response.status_code == 429:
            raise AIProviderError("RATE_LIMITED", "OpenAI rate limit reached.", provider="openai")
        if response.status_code in {401, 403}:
            raise AIProviderError("API_ERROR", "OpenAI API key was rejected.", provider="openai")
        if response.status_code == 402:
            raise AIProviderError(
                "QUOTA_EXCEEDED", "OpenAI billing or quota limit reached.", provider="openai"
            )
        if response.status_code >= 400:
            detail = response.text[:240] if response.text else "OpenAI request failed."
            raise AIProviderError("API_ERROR", detail, provider="openai")
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
