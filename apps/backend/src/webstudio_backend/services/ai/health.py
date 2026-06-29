"""In-memory AI provider health tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from webstudio_backend.services.ai.types import ProviderHealthSnapshot, ProviderId


@dataclass
class _ProviderStats:
    requests: int = 0
    failures: int = 0
    rate_limits: int = 0
    quota_exceeded: int = 0
    last_error: str | None = None
    last_success_at: str | None = None


class AIProviderHealthTracker:
    _lock = Lock()
    _stats: dict[ProviderId, _ProviderStats] = {}

    @classmethod
    def _bucket(cls, provider: ProviderId) -> _ProviderStats:
        with cls._lock:
            return cls._stats.setdefault(provider, _ProviderStats())

    @classmethod
    def record_request(cls, provider: ProviderId) -> None:
        cls._bucket(provider).requests += 1

    @classmethod
    def record_success(cls, provider: ProviderId) -> None:
        bucket = cls._bucket(provider)
        bucket.last_success_at = datetime.now(UTC).isoformat()
        bucket.last_error = None

    @classmethod
    def record_failure(cls, provider: ProviderId, *, message: str) -> None:
        bucket = cls._bucket(provider)
        bucket.failures += 1
        bucket.last_error = message[:512]

    @classmethod
    def record_rate_limit(cls, provider: ProviderId, *, message: str) -> None:
        bucket = cls._bucket(provider)
        bucket.rate_limits += 1
        bucket.failures += 1
        bucket.last_error = message[:512]

    @classmethod
    def record_quota_exceeded(cls, provider: ProviderId, *, message: str) -> None:
        bucket = cls._bucket(provider)
        bucket.quota_exceeded += 1
        bucket.failures += 1
        bucket.last_error = message[:512]

    @classmethod
    def snapshot(
        cls,
        provider: ProviderId,
        *,
        configured: bool,
    ) -> ProviderHealthSnapshot:
        bucket = cls._bucket(provider)
        if not configured:
            status = "not_configured"
        elif bucket.rate_limits > 0 or bucket.quota_exceeded > 0:
            status = "degraded"
        elif bucket.failures > 0 and not bucket.last_success_at:
            status = "unavailable"
        elif bucket.failures > bucket.requests // 2 and bucket.requests >= 3:
            status = "degraded"
        else:
            status = "healthy"
        return ProviderHealthSnapshot(
            provider=provider,
            configured=configured,
            status=status,
            requests=bucket.requests,
            failures=bucket.failures,
            rate_limits=bucket.rate_limits,
            quota_exceeded=bucket.quota_exceeded,
            last_error=bucket.last_error,
            last_success_at=bucket.last_success_at,
        )

    @classmethod
    def all_snapshots(cls, *, configured: dict[ProviderId, bool]) -> list[ProviderHealthSnapshot]:
        return [cls.snapshot(provider, configured=configured.get(provider, False)) for provider in configured]

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._stats.clear()
