"""Health check endpoints."""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.session import get_engine

router = APIRouter(tags=["health"])


def _envelope(request: Request, data: dict) -> dict:
    return Envelope(
        data=data,
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


@router.get("/health/live")
async def health_live(request: Request) -> dict:
    settings = request.app.state.settings
    return _envelope(
        request,
        {
            "status": "ok",
            "version": settings.app_version,
            "api_version": f"v{settings.api_version.split('.')[0]}",
            "min_client_version": settings.min_client_version,
        },
    )


@router.get("/health")
async def health_alias(request: Request) -> dict:
    return await health_live(request)


@router.get("/health/version")
async def health_version(request: Request) -> dict:
    settings = request.app.state.settings
    return _envelope(
        request,
        {
            "app_version": settings.app_version,
            "api_version": settings.api_version,
            "min_client_version": settings.min_client_version,
            "environment": settings.app_env,
            "build_time": None,
            "git_commit": None,
        },
    )


@router.get("/health/ready")
async def health_ready(request: Request) -> JSONResponse:
    checks: dict[str, str] = {
        "database": "unknown",
        "migrations": "ok",
        "disk_space": "unknown",
    }

    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"

    usage = shutil.disk_usage("/")
    free_ratio = usage.free / usage.total if usage.total else 0
    checks["disk_space"] = "ok" if free_ratio >= 0.05 else "failed"

    ready = all(value == "ok" for value in checks.values())
    payload = _envelope(
        request,
        {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
