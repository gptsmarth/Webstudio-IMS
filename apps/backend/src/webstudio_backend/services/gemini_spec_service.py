"""Backward-compatible enrichment service shim."""

from __future__ import annotations

from typing import Any

from webstudio_backend.core.config import Settings
from webstudio_backend.services.ai.config import DEFAULT_GEMINI_MODEL
from webstudio_backend.services.ai.enrichment_service import ProductEnrichmentService
from webstudio_backend.services.ai.json_utils import parse_json_object as _parse_json_object
from webstudio_backend.services.ai.providers.factory import create_provider
from webstudio_backend.services.ai.providers.gemini import GROUNDED_MODELS
from webstudio_backend.services.ai.spec_normalization import (
    normalize_cpu as _normalize_cpu,
    normalize_spec as _normalize_spec,
    response_anchors_model_number as _response_anchors_model_number,
)
from webstudio_backend.services.ai.types import AIProviderConfig, AIProviderError, ProviderCredentials

DEFAULT_MODEL = DEFAULT_GEMINI_MODEL


class GeminiLookupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _to_gemini_error(exc: AIProviderError) -> GeminiLookupError:
    code = exc.code
    if code == "NOT_CONFIGURED":
        code = "SERVICE_UNAVAILABLE"
    return GeminiLookupError(code, exc.message)


class GeminiSpecService:
    """Backward-compatible wrapper around the provider-based enrichment service."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        api_key: str | None = None,
        model: str | None = None,
        session=None,
    ) -> None:
        self._settings = settings
        self._session = session
        env_key = settings.gemini_api_key.strip() if settings else ""
        env_model = settings.gemini_model.strip() if settings else ""
        self._api_key = (api_key or env_key).strip()
        self._model = (model or env_model or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def lookup_laptop_spec(
        self,
        model_number: str,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> dict[str, Any]:
        if self._session is not None:
            service = ProductEnrichmentService(self._session, self._settings)
            try:
                return await service.lookup_laptop_spec(
                    model_number,
                    model_name=model_name,
                    brand_name=brand_name,
                )
            except AIProviderError as exc:
                raise _to_gemini_error(exc) from exc

        provider = create_provider("gemini", _build_inline_config(self._api_key, self._model))
        if not provider.is_configured():
            raise GeminiLookupError(
                "SERVICE_UNAVAILABLE",
                "Gemini API is not configured. Add your API key in System Settings → Integrations.",
            )
        try:
            result = await provider.enrich_product_spec(
                model_number,
                brand_name=brand_name,
                model_name=model_name,
            )
            from webstudio_backend.services.product_image_service import resolve_product_image

            payload = result.to_dict()
            payload["product_image_url"] = await resolve_product_image(
                model_number=model_number,
                brand_name=brand_name,
                model_name=result.model_name,
                candidate_url=result.product_image_url,
                grounding_body=result.grounding_body,
                image_search_query=result.image_search_query,
            )
            return payload
        except AIProviderError as exc:
            raise _to_gemini_error(exc) from exc

    async def lookup_product_image(
        self,
        model_number: str,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not self.is_configured:
            return None, None
        provider = create_provider("gemini", _build_inline_config(self._api_key, self._model))
        query = await provider.generate_image_search_query(
            model_number,
            brand_name=brand_name,
            model_name=model_name,
        )
        from webstudio_backend.services.product_image_service import resolve_product_image

        image_url = await resolve_product_image(
            model_number=model_number,
            brand_name=brand_name,
            model_name=model_name,
            image_search_query=query,
        )
        return image_url, None


def _build_inline_config(api_key: str, model: str) -> AIProviderConfig:
    return AIProviderConfig(
        gemini=ProviderCredentials(provider="gemini", api_key=api_key, model=model),
    )


# Backward-compatible exports for existing tests and callers.
__all__ = [
    "DEFAULT_MODEL",
    "GROUNDED_MODELS",
    "GeminiLookupError",
    "GeminiSpecService",
    "_normalize_cpu",
    "_normalize_spec",
    "_parse_json_object",
    "_response_anchors_model_number",
]
