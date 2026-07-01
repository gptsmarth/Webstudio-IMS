"""HTTP request logging middleware."""

from __future__ import annotations

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from webstudio_backend.core.request_context import get_correlation_id, get_request_id


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        rounded_ms = round(duration_ms, 2)
        threshold_ms = float(getattr(request.app.state.settings, "slow_request_threshold_ms", 750))
        response_bytes = response.headers.get("content-length")
        log_kwargs = {
            "request_id": get_request_id(request),
            "correlation_id": get_correlation_id(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": rounded_ms,
        }
        if response_bytes is not None:
            try:
                log_kwargs["response_bytes"] = int(response_bytes)
            except ValueError:
                pass
        bound = logger.bind(**log_kwargs)
        if rounded_ms >= threshold_ms:
            bound.warning("http_request_slow")
        else:
            bound.info("http_request")
        return response
