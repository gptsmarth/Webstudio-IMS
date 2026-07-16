"""Groq AI provider (OpenAI-compatible chat completions)."""

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

DEFAULT_MODEL = "llama-3.3-70b-versatile"
API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    provider_id = "groq"

    def __init__(self, config: AIProviderConfig) -> None:
        super().__init__(config)
        self._api_key = config.groq.api_key.strip()
        self._model = config.groq.model.strip() or DEFAULT_MODEL

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
            raise AIProviderError("NOT_CONFIGURED", "Groq API is not configured.", provider="groq")

        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.", provider="groq")

        prompt = build_spec_lookup_prompt(
            sku, brand_name=brand_name, model_name=model_name, use_web_search=False
        )
        started = time.perf_counter()
        AIProviderHealthTracker.record_request("groq")

        try:
            body = await self._chat(prompt, json_mode=True)
            text = _extract_chat_text(body)
            parsed_raw = parse_json_object(text or "")
            if not parsed_raw:
                raise AIProviderError(
                    "NOT_FOUND", "Groq returned an unreadable response.", provider="groq"
                )
            normalized = normalize_spec(parsed_raw, fallback_name=model_name or sku, source="groq")
            if not validate_enrichment_payload(
                normalized,
                model_number=sku,
                provider="groq",
                brand_name=brand_name,
            ):
                raise AIProviderError(
                    "NOT_FOUND",
                    "Groq could not produce validated specifications for this SKU.",
                    provider="groq",
                )
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info("Groq enrichment succeeded for {} in {}ms", sku, duration_ms)
            AIProviderHealthTracker.record_success("groq")
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
                source="groq",
                provider="groq",
                confidence_score=float(normalized.get("confidence_score") or 0.65),
                image_search_query=image_query,
            )
        except AIProviderError as exc:
            if exc.code == "RATE_LIMITED":
                AIProviderHealthTracker.record_rate_limit("groq", message=exc.message)
            elif exc.code == "QUOTA_EXCEEDED":
                AIProviderHealthTracker.record_quota_exceeded("groq", message=exc.message)
            else:
                AIProviderHealthTracker.record_failure("groq", message=exc.message)
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
                provider="groq", success=False, message="Groq API key is not configured."
            )
        started = time.perf_counter()
        try:
            await self._chat('Respond with JSON: {"status":"ok"}', json_mode=True)
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                provider="groq",
                success=True,
                message=f"Connected to Groq model {self._model}.",
                latency_ms=latency,
            )
        except AIProviderError as exc:
            return ProviderTestResult(provider="groq", success=False, message=exc.message)

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
            raise AIProviderError("TIMEOUT", "Groq request timed out.", provider="groq") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("API_ERROR", "Could not reach Groq.", provider="groq") from exc

        if response.status_code == 429:
            raise AIProviderError("RATE_LIMITED", "Groq rate limit reached.", provider="groq")
        if response.status_code in {401, 403}:
            raise AIProviderError("API_ERROR", "Groq API key was rejected.", provider="groq")
        if response.status_code == 402:
            raise AIProviderError("QUOTA_EXCEEDED", "Groq quota exceeded.", provider="groq")
        if response.status_code >= 400:
            raise AIProviderError("API_ERROR", "Groq request failed.", provider="groq")
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
