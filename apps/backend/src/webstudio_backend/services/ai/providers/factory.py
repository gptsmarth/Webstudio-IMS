"""AI provider factory."""

from __future__ import annotations

from webstudio_backend.services.ai.providers.base import AIProvider
from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.providers.groq import GroqProvider
from webstudio_backend.services.ai.providers.mock import MockProvider
from webstudio_backend.services.ai.providers.openrouter import OpenRouterProvider
from webstudio_backend.services.ai.types import AIProviderConfig, ProviderId

_PROVIDER_CLASSES: dict[ProviderId, type[AIProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "mock": MockProvider,
}


def create_provider(provider_id: ProviderId, config: AIProviderConfig) -> AIProvider:
    provider_cls = _PROVIDER_CLASSES.get(provider_id)
    if provider_cls is None:
        raise ValueError(f"Unknown AI provider: {provider_id}")
    return provider_cls(config)

def build_provider_chain(config: AIProviderConfig) -> list[AIProvider]:
    chain: list[AIProvider] = []
    seen: set[ProviderId] = set()
    for provider_id in config.fallback_chain:
        if provider_id in seen:
            continue
        seen.add(provider_id)
        chain.append(create_provider(provider_id, config))
    if not chain:
        chain.append(create_provider(config.primary_provider, config))
    return chain
