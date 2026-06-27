"""Metadata placeholder endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.request_context import get_correlation_id, get_request_id

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/info")
async def metadata_info(request: Request) -> dict:
    settings = request.app.state.settings
    return Envelope(
        data={
            "service": "webstudio-ims-api",
            "api_version": settings.api_version,
            "app_version": settings.app_version,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "documentation": "/docs" if settings.is_development else None,
        },
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()
