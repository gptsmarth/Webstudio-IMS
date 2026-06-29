"""AI provider base protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from webstudio_backend.services.ai.types import (
    AIProviderConfig,
    EnrichmentResult,
    ProviderTestResult,
    ProviderId,
)


class AIProvider(ABC):
    provider_id: ProviderId

    def __init__(self, config: AIProviderConfig) -> None:
        self._config = config

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def enrich_product_spec(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> EnrichmentResult:
        raise NotImplementedError

    @abstractmethod
    async def generate_image_search_query(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def test_connection(self) -> ProviderTestResult:
        raise NotImplementedError

    def _timeout(self) -> float:
        return float(self._config.timeout_seconds)

    def _retry_count(self) -> int:
        return self._config.retry_count

    def _provider_source(self) -> str:
        return self.provider_id
