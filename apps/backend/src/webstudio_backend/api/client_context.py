"""Extract client metadata from HTTP requests."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def client_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    if not value:
        return None
    return value[:512]


def client_device_label(request: Request, explicit: str | None = None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip()[:128]
    platform = request.headers.get("x-client-platform")
    if platform:
        return platform[:128]
    return None
