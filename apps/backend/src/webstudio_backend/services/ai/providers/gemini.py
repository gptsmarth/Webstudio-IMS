"""Google Gemini AI provider — web search first, knowledge fallback second."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from loguru import logger

from webstudio_backend.services.ai.gemini_model_stats import (
    most_successful_gemini_model,
    record_gemini_model_success,
)
from webstudio_backend.services.ai.health import AIProviderHealthTracker
from webstudio_backend.services.ai.json_utils import parse_json_object
from webstudio_backend.services.ai.prompts import (
    build_accessory_spec_lookup_prompt,
    build_image_search_query_prompt,
    build_spec_lookup_prompt,
    default_image_search_query,
)
from webstudio_backend.services.ai.providers.base import AIProvider
from webstudio_backend.services.ai.spec_normalization import (
    normalize_accessory_spec,
    normalize_spec,
    validate_accessory_payload,
    validate_enrichment_payload,
)
from webstudio_backend.services.ai.types import (
    AIProviderConfig,
    AIProviderError,
    EnrichmentResult,
    ProviderTestResult,
)

DEFAULT_MODEL = "gemini-2.5-flash-lite"
# Second attempt only — flash-lite is fastest and has a separate quota bucket.
FAST_FALLBACK_MODEL = "gemini-2.5-flash"
MAX_SPEC_LOOKUP_MODELS = 2
RATE_LIMIT_MODEL_SWITCH_DELAY_SECONDS = 0.5


class GeminiProvider(AIProvider):
    provider_id = "gemini"

    def __init__(self, config: AIProviderConfig) -> None:
        super().__init__(config)
        self._api_key = config.gemini.api_key.strip()
        self._model = config.gemini.model.strip() or DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _model_chain(self, *, max_models: int = MAX_SPEC_LOOKUP_MODELS) -> list[str]:
        chain: list[str] = []
        winner = most_successful_gemini_model()
        if winner:
            chain.append(winner)
        for candidate in (self._model, DEFAULT_MODEL, FAST_FALLBACK_MODEL):
            name = candidate.strip()
            if name and name not in chain:
                chain.append(name)
        return chain[:max_models]

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
                "Gemini API is not configured. Add your API key in System Settings → Integrations.",
                provider="gemini",
            )

        sku = model_number.strip()
        if not sku:
            raise AIProviderError("NOT_FOUND", "Model number is required.", provider="gemini")

        grounded_prompt = build_spec_lookup_prompt(
            sku,
            brand_name=brand_name,
            model_name=model_name,
            use_web_search=True,
        )
        parsed, grounding_body, last_error = await self._try_spec_lookup(
            sku,
            prompt=grounded_prompt,
            brand_name=brand_name,
            model_name=model_name,
            use_grounding=True,
            strict_validation=False,
        )
        if parsed is not None:
            return await self._finalize_spec_result(
                parsed,
                sku=sku,
                brand_name=brand_name,
                model_name=model_name,
                grounding_body=grounding_body,
                lookup_mode="web_search",
            )

        knowledge_prompt = build_spec_lookup_prompt(
            sku,
            brand_name=brand_name,
            model_name=model_name,
            use_web_search=False,
        )
        logger.info(
            "Gemini web search did not validate for {}, trying knowledge-only fallback", sku
        )
        parsed_knowledge, knowledge_body, knowledge_error = await self._try_spec_lookup(
            sku,
            prompt=knowledge_prompt,
            brand_name=brand_name,
            model_name=model_name,
            use_grounding=False,
            strict_validation=True,
            models=self._model_chain(max_models=1),
        )
        if parsed_knowledge is not None:
            return await self._finalize_spec_result(
                parsed_knowledge,
                sku=sku,
                brand_name=brand_name,
                model_name=model_name,
                grounding_body=knowledge_body,
                lookup_mode="knowledge",
            )

        if last_error and last_error.code == "RATE_LIMITED":
            raise last_error
        if knowledge_error and knowledge_error.code == "RATE_LIMITED":
            raise knowledge_error
        if last_error:
            raise last_error
        if knowledge_error:
            raise knowledge_error
        raise AIProviderError(
            "NOT_FOUND",
            f"Could not find verified specifications for {sku}. Enter details manually.",
            provider="gemini",
        )

    async def enrich_accessory_spec(
        self,
        identifier: str,
        *,
        identifier_type: str = "model_number",
        brand_name: str | None = None,
        accessory_kind: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise AIProviderError(
                "NOT_CONFIGURED",
                "Gemini API is not configured. Add your API key in System Settings → Integrations.",
                provider="gemini",
            )

        sku = identifier.strip()
        if not sku:
            raise AIProviderError(
                "NOT_FOUND", "Part or model number is required.", provider="gemini"
            )

        prompt = build_accessory_spec_lookup_prompt(
            sku,
            identifier_type=identifier_type,
            brand_name=brand_name,
            model_name=model_name,
            use_web_search=True,
        )
        parsed, grounding_body, last_error = await self._try_accessory_lookup(
            sku,
            prompt=prompt,
            brand_name=brand_name,
            identifier_type=identifier_type,
            use_grounding=True,
        )
        if parsed is not None:
            image_query = default_image_search_query(
                sku,
                brand_name=brand_name,
                model_name=parsed.get("model_name"),
            )
            parsed["image_search_query"] = image_query
            parsed["grounding_body"] = grounding_body
            parsed["provider"] = "gemini"
            return parsed

        knowledge_prompt = build_accessory_spec_lookup_prompt(
            sku,
            identifier_type=identifier_type,
            brand_name=brand_name,
            model_name=model_name,
            use_web_search=False,
        )
        logger.info(
            "Gemini web search did not validate for accessory {}, trying knowledge fallback", sku
        )
        parsed_knowledge, knowledge_body, knowledge_error = await self._try_accessory_lookup(
            sku,
            prompt=knowledge_prompt,
            brand_name=brand_name,
            identifier_type=identifier_type,
            use_grounding=False,
            models=self._model_chain(max_models=1),
        )
        if parsed_knowledge is not None:
            image_query = default_image_search_query(
                sku,
                brand_name=brand_name,
                model_name=parsed_knowledge.get("model_name"),
            )
            parsed_knowledge["image_search_query"] = image_query
            parsed_knowledge["grounding_body"] = knowledge_body
            parsed_knowledge["provider"] = "gemini"
            return parsed_knowledge

        if last_error and last_error.code == "RATE_LIMITED":
            raise last_error
        if knowledge_error and knowledge_error.code == "RATE_LIMITED":
            raise knowledge_error
        if last_error:
            raise last_error
        if knowledge_error:
            raise knowledge_error
        raise AIProviderError(
            "NOT_FOUND",
            f"Could not find verified details for {sku}. Enter details manually.",
            provider="gemini",
        )

    async def _try_accessory_lookup(
        self,
        identifier: str,
        *,
        prompt: str,
        brand_name: str | None,
        identifier_type: str,
        use_grounding: bool,
        models: list[str] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, AIProviderError | None]:
        last_error: AIProviderError | None = None
        for gemini_model in models or self._model_chain():
            started = time.perf_counter()
            AIProviderHealthTracker.record_request("gemini")
            try:
                payload = _build_payload(prompt, use_grounding=use_grounding)
                body = await self._generate(gemini_model, payload)
                parsed = _parse_accessory_body(
                    body,
                    fallback_name=identifier,
                    identifier=identifier,
                    identifier_type=identifier_type,
                    brand_name=brand_name,
                )
                if not parsed:
                    continue
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "Gemini accessory lookup succeeded for {} ({}) via {} in {}ms",
                    identifier,
                    identifier_type,
                    gemini_model,
                    duration_ms,
                )
                record_gemini_model_success(gemini_model)
                AIProviderHealthTracker.record_success("gemini")
                return parsed, body, None
            except AIProviderError as exc:
                last_error = exc
                if exc.code == "RATE_LIMITED":
                    AIProviderHealthTracker.record_rate_limit("gemini", message=exc.message)
                    await asyncio.sleep(RATE_LIMIT_MODEL_SWITCH_DELAY_SECONDS)
                    continue
                AIProviderHealthTracker.record_failure("gemini", message=exc.message)
        return None, None, last_error

    async def _try_spec_lookup(
        self,
        sku: str,
        *,
        prompt: str,
        brand_name: str | None,
        model_name: str | None,
        use_grounding: bool,
        strict_validation: bool,
        models: list[str] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, AIProviderError | None]:
        last_error: AIProviderError | None = None
        rate_limited = False
        last_body: dict[str, Any] | None = None

        for gemini_model in models or self._model_chain():
            started = time.perf_counter()
            AIProviderHealthTracker.record_request("gemini")
            try:
                payload = _build_payload(prompt, use_grounding=use_grounding)
                body = await self._generate(gemini_model, payload)
                parsed = _parse_lookup_body(
                    body,
                    fallback_name=model_name or sku,
                    model_number=sku,
                    brand_name=brand_name,
                    strict_validation=strict_validation,
                )
                if not parsed:
                    continue
                duration_ms = int((time.perf_counter() - started) * 1000)
                mode = "grounded" if use_grounding else "knowledge"
                logger.info(
                    "Gemini {} lookup succeeded for {} via {} in {}ms",
                    mode,
                    sku,
                    gemini_model,
                    duration_ms,
                )
                record_gemini_model_success(gemini_model)
                AIProviderHealthTracker.record_success("gemini")
                return parsed, body, None
            except AIProviderError as exc:
                last_error = exc
                if exc.code == "RATE_LIMITED":
                    rate_limited = True
                    AIProviderHealthTracker.record_rate_limit("gemini", message=exc.message)
                    logger.info("Gemini model {} rate-limited, trying next", gemini_model)
                    await asyncio.sleep(RATE_LIMIT_MODEL_SWITCH_DELAY_SECONDS)
                    continue
                if exc.code in {"API_ERROR", "TIMEOUT"} and rate_limited:
                    continue
                if exc.code == "API_ERROR" and "unsupported" in exc.message.lower():
                    AIProviderHealthTracker.record_failure("gemini", message=exc.message)
                    continue
                AIProviderHealthTracker.record_failure("gemini", message=exc.message)
                if not use_grounding:
                    raise

        if rate_limited and use_grounding:
            return (
                None,
                last_body,
                AIProviderError(
                    "RATE_LIMITED",
                    "Gemini web search quota exhausted. Knowledge fallback also failed or was skipped.",
                    provider="gemini",
                ),
            )
        return None, last_body, last_error

    async def _finalize_spec_result(
        self,
        parsed: dict[str, Any],
        *,
        sku: str,
        brand_name: str | None,
        model_name: str | None,
        grounding_body: dict[str, Any] | None,
        lookup_mode: str,
    ) -> EnrichmentResult:
        image_query = default_image_search_query(
            sku,
            brand_name=brand_name,
            model_name=parsed.get("model_name") or model_name,
        )
        notes = parsed.get("notes") or ""
        if sku.upper() not in notes.upper():
            source_note = f"Matched listing for {sku} ({lookup_mode})"
            parsed["notes"] = f"{notes}\n---\n{source_note}".strip() if notes else source_note

        return _to_enrichment_result(
            parsed,
            provider="gemini",
            image_search_query=image_query,
            grounding_body=grounding_body,
        )

    async def generate_image_search_query(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> str:
        fallback = default_image_search_query(
            model_number,
            brand_name=brand_name,
            model_name=model_name,
        )
        if not self.is_configured():
            return fallback

        prompt = build_image_search_query_prompt(
            model_number,
            brand_name=brand_name,
            model_name=model_name,
        )
        for use_grounding in (True, False):
            for gemini_model in self._model_chain()[:2]:
                try:
                    payload = _build_payload(prompt, use_grounding=use_grounding)
                    body = await self._generate(gemini_model, payload)
                    text = _extract_text(body)
                    parsed = parse_json_object(text or "")
                    if parsed and isinstance(parsed.get("image_search_query"), str):
                        query = parsed["image_search_query"].strip()
                        if query:
                            return query[:256]
                except AIProviderError:
                    continue
        return fallback

    async def test_connection(self) -> ProviderTestResult:
        if not self.is_configured():
            return ProviderTestResult(
                provider="gemini",
                success=False,
                message="Gemini API key is not configured.",
            )
        started = time.perf_counter()
        try:
            payload = _build_payload('Respond with JSON: {"status":"ok"}', use_grounding=False)
            await self._generate(self._model, payload)
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                provider="gemini",
                success=True,
                message=f"Connected to Gemini model {self._model}.",
                latency_ms=latency,
            )
        except AIProviderError as exc:
            return ProviderTestResult(provider="gemini", success=False, message=exc.message)

    async def _generate(self, gemini_model: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "TIMEOUT", "Gemini request timed out.", provider="gemini"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Gemini network error for {}: {}", gemini_model, type(exc).__name__)
            raise AIProviderError(
                "API_ERROR",
                "Could not reach Gemini. Check your internet connection and try again.",
                provider="gemini",
            ) from exc

        if response.status_code == 429:
            raise AIProviderError(
                "RATE_LIMITED", _parse_rate_limit_message(response), provider="gemini"
            )
        if response.status_code in {401, 403}:
            raise AIProviderError(
                "API_ERROR",
                "Gemini API key was rejected. Create a new key at https://aistudio.google.com/apikey",
                provider="gemini",
            )
        if response.status_code == 404:
            raise AIProviderError(
                "API_ERROR",
                f"Gemini model '{gemini_model}' is not available for this API key.",
                provider="gemini",
            )
        if response.status_code == 400:
            raise AIProviderError(
                "API_ERROR",
                _error_message(response) or "Gemini rejected the request.",
                provider="gemini",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _error_message(response) or f"HTTP {response.status_code}"
            raise AIProviderError(
                "API_ERROR",
                f"Gemini request failed ({detail}).",
                provider="gemini",
            ) from exc
        return response.json()


def _build_payload(prompt: str, use_grounding: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }
    if use_grounding:
        payload["tools"] = [{"google_search": {}}]
    else:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    return payload


def _extract_text(body: dict[str, Any]) -> str | None:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    text = parts[0].get("text") if isinstance(parts[0], dict) else None
    return text if isinstance(text, str) else None


def _parse_lookup_body(
    body: dict[str, Any],
    *,
    fallback_name: str,
    model_number: str,
    brand_name: str | None = None,
    strict_validation: bool = False,
) -> dict[str, Any] | None:
    text = _extract_text(body)
    if not text:
        return None
    parsed = parse_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON text: {}", text[:200])
        return None
    normalized = normalize_spec(parsed, fallback_name=fallback_name, source="gemini")
    provider_key = "groq" if strict_validation else "gemini"
    if not validate_enrichment_payload(
        normalized,
        model_number=model_number,
        provider=provider_key,
        brand_name=brand_name,
    ):
        logger.info(
            "Gemini payload rejected for {} (strict={})",
            model_number,
            strict_validation,
        )
        return None
    return normalized


def _parse_accessory_body(
    body: dict[str, Any],
    *,
    fallback_name: str,
    identifier: str,
    identifier_type: str = "model_number",
    brand_name: str | None = None,
) -> dict[str, Any] | None:
    text = _extract_text(body)
    if not text:
        return None
    parsed = parse_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON accessory text: {}", text[:200])
        return None
    normalized = normalize_accessory_spec(
        parsed,
        fallback_name=fallback_name,
        identifier=identifier,
        identifier_type=identifier_type,
        source="gemini",
    )
    if not validate_accessory_payload(
        normalized,
        identifier=identifier,
        identifier_type=identifier_type,
    ):
        logger.info("Gemini accessory payload rejected for {} ({})", identifier, identifier_type)
        return None
    return normalized


def _to_enrichment_result(
    parsed: dict[str, Any],
    *,
    provider: str,
    image_search_query: str,
    grounding_body: dict[str, Any] | None,
) -> EnrichmentResult:
    return EnrichmentResult(
        model_name=parsed["model_name"],
        cpu=parsed["cpu"],
        gpu=parsed.get("gpu"),
        ram_gb=int(parsed["ram_gb"]),
        storage_value=parsed["storage_value"],
        storage_unit=parsed["storage_unit"],
        storage_type=parsed["storage_type"],
        display=parsed.get("display"),
        color_options=parsed.get("color_options"),
        product_image_url=None,
        description=parsed.get("description"),
        notes=parsed.get("notes"),
        source="gemini",
        provider=provider,  # type: ignore[arg-type]
        confidence_score=float(parsed.get("confidence_score") or 0.85),
        image_search_query=image_search_query,
        grounding_body=grounding_body,
    )


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", {}).get("message", ""))
    except (json.JSONDecodeError, AttributeError):
        return ""


def _parse_rate_limit_message(response: httpx.Response) -> str:
    try:
        message = response.json().get("error", {}).get("message", "")
        if "Please retry in" in message:
            return f"Gemini rate limit: {message.split('Please retry in')[-1].strip()}"
    except (json.JSONDecodeError, AttributeError):
        pass
    return "Gemini rate limit reached. Wait a few minutes and try again."
