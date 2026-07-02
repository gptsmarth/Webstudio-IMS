"""Server host validation — IPv4, hostname, and .local mDNS names."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass

_HOSTNAME_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$",
)


class HostValidationError(ValueError):
    pass


@dataclass(slots=True)
class HostResolution:
    configured_host: str
    resolved_ip: str | None
    success: bool
    message: str


def normalize_server_host(raw: str) -> str:
    host = raw.strip()
    if not host:
        raise HostValidationError("Host / IP address is required.")
    if len(host) > 253:
        raise HostValidationError("Host / IP address is too long.")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    lowered = host.lower().removesuffix(".")
    if not _HOSTNAME_PATTERN.fullmatch(lowered):
        raise HostValidationError(
            "Enter a valid IPv4 address, hostname, or mDNS name (for example WEBSTUDIO-SERVER.local).",
        )
    return lowered


async def resolve_server_host(host: str, *, port: int = 8000) -> HostResolution:
    configured = normalize_server_host(host)
    try:
        loop = asyncio.get_running_loop()
        results = await loop.getaddrinfo(
            configured,
            port,
            type=socket.SOCK_STREAM,
            family=socket.AF_INET,
        )
        if not results:
            return HostResolution(
                configured_host=configured,
                resolved_ip=None,
                success=False,
                message=f"Could not resolve {configured}.",
            )
        resolved_ip = results[0][4][0]
        return HostResolution(
            configured_host=configured,
            resolved_ip=resolved_ip,
            success=True,
            message=f"Resolved {configured} to {resolved_ip}.",
        )
    except socket.gaierror as exc:
        return HostResolution(
            configured_host=configured,
            resolved_ip=None,
            success=False,
            message=f"DNS lookup failed for {configured}: {exc.strerror or exc}.",
        )
    except HostValidationError as exc:
        return HostResolution(
            configured_host=host.strip(),
            resolved_ip=None,
            success=False,
            message=str(exc),
        )
