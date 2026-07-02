"""LAN discovery health metadata — public, no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.network.host_validation import (
    HostValidationError,
    normalize_server_host,
    resolve_server_host,
)
from webstudio_backend.services.discovery_health_service import build_discovery_health_payload

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.get(
    "/health",
    summary="Discovery health metadata",
    description=(
        "Returns server metadata for LAN discovery clients: online status, versions, "
        "company name, and database status. Does not expose secrets or user data."
    ),
)
async def discovery_health(request: Request, db_session: AsyncSession = DbSessionDep) -> dict:
    settings = request.app.state.settings
    payload = await build_discovery_health_payload(db_session, settings)
    return build_envelope(request, payload)


@router.get(
    "/validate-host",
    summary="Validate and resolve a server hostname",
    description=(
        "Validates IPv4, hostname, or .local mDNS names and optionally resolves them. "
        "Used by clients for connection diagnostics — does not expose credentials."
    ),
)
async def validate_host(request: Request, host: str, port: int = 8000) -> dict:
    try:
        normalized = normalize_server_host(host)
    except HostValidationError as exc:
        return build_envelope(
            request,
            {
                "valid": False,
                "host": host.strip(),
                "message": str(exc),
            },
        )

    resolution = await resolve_server_host(normalized, port=port)
    return build_envelope(
        request,
        {
            "valid": True,
            "host": normalized,
            "resolved_ip": resolution.resolved_ip,
            "resolved": resolution.success,
            "message": resolution.message,
        },
    )
