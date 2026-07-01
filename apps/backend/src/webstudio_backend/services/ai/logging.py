"""Structured logging helpers for the AI provider layer."""

from __future__ import annotations

from typing import Any

from loguru import logger

_LAYER = "ai"


def _bind(**context: Any):
    return logger.bind(layer=_LAYER, **{key: value for key, value in context.items() if value is not None})


def log_enrichment_start(*, sku: str, attempt: int, max_attempts: int, providers: list[str]) -> None:
    _bind(event="enrichment_start", sku=sku, attempt=attempt, max_attempts=max_attempts, providers=providers).info(
        "AI enrichment started for {}",
        sku,
    )


def log_enrichment_retry(*, sku: str, attempt: int, max_attempts: int, delay_seconds: float) -> None:
    _bind(
        event="enrichment_retry",
        sku=sku,
        attempt=attempt,
        max_attempts=max_attempts,
        delay_seconds=delay_seconds,
    ).info(
        "AI enrichment retry {}/{} for {} in {:.0f}s",
        attempt,
        max_attempts,
        sku,
        delay_seconds,
    )


def log_provider_attempt(*, provider: str, sku: str, attempt: int) -> None:
    _bind(event="provider_attempt", provider=provider, sku=sku, attempt=attempt).debug(
        "Trying provider {} for {}",
        provider,
        sku,
    )


def log_provider_success(
    *,
    provider: str,
    sku: str,
    duration_ms: int,
    confidence: float,
    cached: bool = False,
) -> None:
    _bind(
        event="provider_success",
        provider=provider,
        sku=sku,
        duration_ms=duration_ms,
        confidence=confidence,
        cached=cached,
    ).info(
        "AI enrichment succeeded via {} for {} in {}ms (confidence={:.2f})",
        provider,
        sku,
        duration_ms,
        confidence,
    )


def log_provider_failure(*, provider: str, sku: str, duration_ms: int, code: str, message: str) -> None:
    _bind(
        event="provider_failure",
        provider=provider,
        sku=sku,
        duration_ms=duration_ms,
        error_code=code,
        error_message=message,
    ).warning(
        "AI enrichment failed via {} for {} after {}ms: {}",
        provider,
        sku,
        duration_ms,
        message,
    )


def log_cache_hit(*, sku: str, provider: str) -> None:
    _bind(event="cache_hit", sku=sku, provider=provider).info("AI enrichment cache hit for {}", sku)


def log_cache_stale(*, sku: str) -> None:
    _bind(event="cache_stale", sku=sku).info("Stale AI enrichment cache rejected for {}, refreshing", sku)


def log_database_reuse(*, sku: str) -> None:
    _bind(event="database_reuse", sku=sku).info("Reusing existing product model enrichment for {}", sku)


def log_provider_test(*, provider: str, success: bool, latency_ms: int | None, message: str) -> None:
    _bind(
        event="provider_test",
        provider=provider,
        success=success,
        latency_ms=latency_ms,
    ).info("AI provider test {}: {}", provider, message)
