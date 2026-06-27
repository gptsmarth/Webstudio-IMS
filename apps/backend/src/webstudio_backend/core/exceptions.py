"""Shared API error types and handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from webstudio_backend.api.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from webstudio_backend.api.schemas.responses import utc_now_iso
from webstudio_backend.core.request_context import get_correlation_id, get_request_id


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


def _error_payload(
    request: Request,
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    body = ErrorResponse(
        error={
            "code": code,
            "message": message,
            "details": details or [],
        },
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    )
    return body.model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, exc.code, exc.message, exc.details),
            headers=_response_headers(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code: ErrorCode = "INTERNAL_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 403:
            code = "PERMISSION_DENIED"
        elif exc.status_code == 401:
            code = "INVALID_CREDENTIALS"
        elif exc.status_code == 409:
            code = "VALIDATION_ERROR"
        elif exc.status_code == 422:
            code = "VALIDATION_ERROR"
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, code, message),
            headers=_response_headers(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in error.get("loc", []) if part != "body"),
                code="VALIDATION_ERROR",
                message=error.get("msg", "Validation error"),
            )
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                request,
                "VALIDATION_ERROR",
                "Request validation failed.",
                details,
            ),
            headers=_response_headers(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_payload(request, "INTERNAL_ERROR", "An unexpected error occurred."),
            headers=_response_headers(request),
        )


def _response_headers(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "X-Request-ID": get_request_id(request),
        "X-Correlation-ID": get_correlation_id(request),
        "API-Version": settings.api_version,
    }
