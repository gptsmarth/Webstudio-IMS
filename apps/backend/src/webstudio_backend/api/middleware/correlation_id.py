"""Correlation and request ID middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from webstudio_backend.core.request_context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    generate_request_id,
    set_request_context,
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or generate_request_id()
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        set_request_context(request_id, correlation_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        response.headers["API-Version"] = request.app.state.settings.api_version
        return response
