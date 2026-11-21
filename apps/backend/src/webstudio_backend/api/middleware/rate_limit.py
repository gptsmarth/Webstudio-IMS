"""In-memory, per-IP rate limiting.

WEBSTUDIO runs as a single process per shop with no shared cache (no Redis),
so limits are tracked in-process. That's the right tradeoff here: this API
is meant to be reached only by a handful of staff devices on a shop's LAN,
not a fleet of servers, so an in-memory sliding window is enough to blunt
abuse from any device on the network without adding infrastructure.

Two limits apply:
  * a general per-IP limit across the whole API (``rate_limit_per_minute``)
  * a tighter per-IP limit on login/refresh (``auth_rate_limit_per_minute``),
    since the existing account lockout only tracks failed attempts per
    username — it does nothing to stop one source on the network from
    trying many different usernames.
"""

from __future__ import annotations

import time
from collections import deque
from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/main-admin/recover-password",
}
_WINDOW_SECONDS = 60.0
_MAX_TRACKED_CLIENTS = 2000


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        requests_per_minute: int,
        auth_requests_per_minute: int,
    ) -> None:
        super().__init__(app)
        self._limit = max(requests_per_minute, 1)
        self._auth_limit = max(min(auth_requests_per_minute, self._limit), 1)
        self._hits: dict[str, tuple[deque[float], deque[float]]] = {}
        self._next_cleanup = 0.0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        is_auth_request = request.method == "POST" and request.url.path.rstrip("/") in _AUTH_PATHS

        now = time.monotonic()
        if now >= self._next_cleanup:
            self._hits = {
                key: buckets
                for key, buckets in self._hits.items()
                if now - buckets[0][-1] < _WINDOW_SECONDS
            }
            self._next_cleanup = now + _WINDOW_SECONDS

        buckets = self._hits.get(client_ip)
        if buckets is None:
            if len(self._hits) >= _MAX_TRACKED_CLIENTS:
                return _rate_limited(self._next_cleanup - now)
            buckets = self._hits[client_ip] = (deque(), deque())

        general, auth = buckets
        active_limits = [(general, self._limit)]
        if is_auth_request:
            active_limits.append((auth, self._auth_limit))
        retry_after = 0.0
        for bucket, limit in active_limits:
            while bucket and now - bucket[0] >= _WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(retry_after, _WINDOW_SECONDS - (now - bucket[0]))
        if retry_after:
            return _rate_limited(retry_after)

        for bucket, _ in active_limits:
            bucket.append(now)
        return await call_next(request)


def _rate_limited(retry_after: float) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please slow down and try again shortly.",
                "details": [],
            }
        },
        headers={"Retry-After": str(max(1, ceil(retry_after)))},
    )
