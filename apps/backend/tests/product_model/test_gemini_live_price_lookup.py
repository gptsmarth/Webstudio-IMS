"""Direct unit tests for GeminiProvider.lookup_live_price's internal
multi-model retry behavior — the service-layer tests in
test_asus_live_price.py monkeypatch this method entirely, so they never
exercise the retry loop itself.
"""

from __future__ import annotations

import pytest

from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.types import (
    AIProviderConfig,
    AIProviderError,
    ProviderCredentials,
)


def _config(api_key: str = "fake-key") -> AIProviderConfig:
    return AIProviderConfig(
        gemini=ProviderCredentials("gemini", api_key=api_key, model="gemini-2.5-flash-lite")
    )


def _body_for(
    price: object, confidence: str, source_url: str | None = "https://in.store.asus.com/x.html"
) -> dict:
    import json

    payload = {"price": price, "source_url": source_url, "confidence": confidence}
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


@pytest.mark.asyncio
async def test_not_configured_never_calls_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(_config(api_key=""))

    async def fail_if_called(self, gemini_model, payload):
        raise AssertionError("should never call _generate when not configured")

    monkeypatch.setattr(GeminiProvider, "_generate", fail_if_called)
    result = await provider.lookup_live_price("X515", brand_name="ASUS", model_name="Vivobook 15")
    assert result is None


@pytest.mark.asyncio
async def test_second_model_used_after_first_hard_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(_config())
    calls: list[str] = []

    async def fake_generate(self, gemini_model, payload):
        calls.append(gemini_model)
        if len(calls) == 1:
            raise AIProviderError("API_ERROR", "boom", provider="gemini")
        return _body_for(81990, "high")

    monkeypatch.setattr(GeminiProvider, "_generate", fake_generate)
    result = await provider.lookup_live_price("M1605NAQ-MB095WS")
    assert result is not None
    assert result["price"] == 81990
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_low_confidence_result_is_not_final_if_a_later_model_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiProvider(_config())
    calls: list[str] = []

    async def fake_generate(self, gemini_model, payload):
        calls.append(gemini_model)
        if len(calls) == 1:
            return _body_for(50000, "low")
        return _body_for(81990, "high")

    monkeypatch.setattr(GeminiProvider, "_generate", fake_generate)
    result = await provider.lookup_live_price("M1605NAQ-MB095WS")
    assert result is not None
    assert result["price"] == 81990
    assert result["confidence"] == "high"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_returns_best_effort_result_when_every_model_comes_up_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiProvider(_config())

    async def fake_generate(self, gemini_model, payload):
        return _body_for(None, "low", source_url=None)

    monkeypatch.setattr(GeminiProvider, "_generate", fake_generate)
    result = await provider.lookup_live_price("AC65-06")
    # Never returns None just because no model found a real price — the
    # caller (refresh_asus_live_price) is responsible for mapping a null
    # price to "not_found"; this method only returns None on hard failure.
    assert result is not None
    assert result["price"] is None


@pytest.mark.asyncio
async def test_rate_limit_on_first_model_falls_through_to_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiProvider(_config())
    calls: list[str] = []

    async def fake_generate(self, gemini_model, payload):
        calls.append(gemini_model)
        if len(calls) == 1:
            raise AIProviderError("RATE_LIMITED", "slow down", provider="gemini")
        return _body_for(129990, "high")

    monkeypatch.setattr(GeminiProvider, "_generate", fake_generate)
    result = await provider.lookup_live_price("V3607VJ-TK227WS")
    assert result is not None
    assert result["price"] == 129990
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_returns_none_when_every_model_hard_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(_config())

    async def fake_generate(self, gemini_model, payload):
        raise AIProviderError("API_ERROR", "boom", provider="gemini")

    monkeypatch.setattr(GeminiProvider, "_generate", fake_generate)
    result = await provider.lookup_live_price("X515")
    assert result is None
