"""mDNS / Bonjour constants for WEBSTUDIO IMS server advertisement."""

from __future__ import annotations

from enum import StrEnum

# Bonjour service type — clients browse for this on the LAN.
DISCOVERY_SERVICE_TYPE = "_webstudio-ims._tcp.local."
DISCOVERY_PROTOCOL_VERSION = "1"


class DiscoveryTxtKey(StrEnum):
    SERVER_NAME = "server_name"
    COMPANY_NAME = "company_name"
    BACKEND_VERSION = "backend_version"
    API_VERSION = "api_version"
    BACKEND_PORT = "backend_port"
    ENVIRONMENT = "environment"
    BUILD_VERSION = "build_version"
    PROTOCOL_VERSION = "protocol_version"
