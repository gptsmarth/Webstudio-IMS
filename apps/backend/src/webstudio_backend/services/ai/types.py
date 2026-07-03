"""Shared types for the AI provider framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProviderId = Literal["gemini", "groq", "openrouter", "mock"]

ProviderErrorCode = Literal[
    "NOT_CONFIGURED",
    "NOT_FOUND",
    "RATE_LIMITED",
    "QUOTA_EXCEEDED",
    "TIMEOUT",
    "API_ERROR",
    "SERVICE_UNAVAILABLE",
]


@dataclass(frozen=True)
class ProviderCredentials:
    provider: ProviderId
    api_key: str = ""
    model: str = ""


@dataclass
class AIProviderConfig:
    primary_provider: ProviderId = "gemini"
    fallback_chain: list[ProviderId] = field(default_factory=lambda: ["gemini"])
    enrichment_enabled: bool = True
    timeout_seconds: int = 90
    retry_count: int = 2
    gemini: ProviderCredentials = field(default_factory=lambda: ProviderCredentials("gemini"))
    groq: ProviderCredentials = field(default_factory=lambda: ProviderCredentials("groq"))
    openrouter: ProviderCredentials = field(
        default_factory=lambda: ProviderCredentials("openrouter")
    )


@dataclass
class EnrichmentResult:
    model_name: str
    cpu: str
    gpu: str | None
    ram_gb: int
    storage_value: str
    storage_unit: str
    storage_type: str
    display: str | None
    color_options: str | None
    product_image_url: str | None
    description: str | None
    notes: str | None
    source: str
    provider: ProviderId
    confidence_score: float
    image_search_query: str | None = None
    grounding_body: dict[str, Any] | None = None
    cached: bool = False
    partial: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "cpu": self.cpu,
            "gpu": self.gpu,
            "ram_gb": self.ram_gb,
            "storage_value": self.storage_value,
            "storage_unit": self.storage_unit,
            "storage_type": self.storage_type,
            "display": self.display,
            "color_options": self.color_options,
            "product_image_url": self.product_image_url,
            "description": self.description,
            "notes": self.notes,
            "source": self.source,
            "provider": self.provider,
            "confidence_score": self.confidence_score,
            "image_search_query": self.image_search_query,
            "cached": self.cached,
            "partial": self.partial,
        }


class AIProviderError(Exception):
    def __init__(
        self, code: ProviderErrorCode, message: str, *, provider: ProviderId | None = None
    ) -> None:
        self.code = code
        self.message = message
        self.provider = provider
        super().__init__(message)


@dataclass
class ProviderTestResult:
    provider: ProviderId
    success: bool
    message: str
    latency_ms: int | None = None


@dataclass
class ProviderHealthSnapshot:
    provider: ProviderId
    configured: bool
    status: str
    requests: int = 0
    failures: int = 0
    rate_limits: int = 0
    quota_exceeded: int = 0
    last_error: str | None = None
    last_success_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": self.configured,
            "status": self.status,
            "requests": self.requests,
            "failures": self.failures,
            "rate_limits": self.rate_limits,
            "quota_exceeded": self.quota_exceeded,
            "last_error": self.last_error,
            "last_success_at": self.last_success_at,
        }
