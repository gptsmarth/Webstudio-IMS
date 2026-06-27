"""Request-scoped identifiers."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_request_id() -> str:
    return str(uuid4())


def set_request_context(request_id: str, correlation_id: str) -> None:
    _request_id_ctx.set(request_id)
    _correlation_id_ctx.set(correlation_id)


def get_request_id(request: Request | None = None) -> str:
    if request is not None and hasattr(request.state, "request_id"):
        return request.state.request_id
    return _request_id_ctx.get() or generate_request_id()


def get_correlation_id(request: Request | None = None) -> str:
    if request is not None and hasattr(request.state, "correlation_id"):
        return request.state.correlation_id
    return _correlation_id_ctx.get() or get_request_id(request)
