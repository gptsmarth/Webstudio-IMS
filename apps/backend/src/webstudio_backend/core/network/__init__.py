"""Network utilities for host validation and LAN discovery."""

from webstudio_backend.core.network.discovery_constants import (
    DISCOVERY_SERVICE_TYPE,
    DiscoveryTxtKey,
)
from webstudio_backend.core.network.host_validation import (
    HostValidationError,
    normalize_server_host,
    resolve_server_host,
)

__all__ = [
    "DISCOVERY_SERVICE_TYPE",
    "DiscoveryTxtKey",
    "HostValidationError",
    "normalize_server_host",
    "resolve_server_host",
]
