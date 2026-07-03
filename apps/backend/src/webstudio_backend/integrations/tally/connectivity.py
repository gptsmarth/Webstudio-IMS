"""Tally workstation connectivity — runtime DNS resolution and staged probes."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

logger = logging.getLogger(__name__)

_HOSTNAME_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$",
)
_CONNECTION_TEST_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Connection Test</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""


class TallyConnectivityStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    RESOLVING = "resolving"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    XML_ERROR = "xml_error"
    CONFIGURATION_ERROR = "configuration_error"


class TallyConnectionStage(StrEnum):
    HOST_RESOLUTION = "host_resolution"
    TCP_CONNECTION = "tcp_connection"
    XML_SERVER = "xml_server"


@dataclass(slots=True)
class TallyConnectionStageResult:
    stage: TallyConnectionStage
    success: bool
    message: str


@dataclass(slots=True)
class TallyHostResolution:
    configured_host: str
    resolved_ip: str | None
    success: bool
    message: str


@dataclass(slots=True)
class TallyConnectionDiagnostics:
    reachable: bool
    host_resolved: bool
    tcp_connected: bool
    xml_responding: bool
    configured_host: str
    resolved_ip: str | None
    port: str
    tally_version: str | None = None
    company_name: str | None = None
    stages: list[TallyConnectionStageResult] = field(default_factory=list)
    user_message: str = ""
    technical_detail: str | None = None
    status: TallyConnectivityStatus = TallyConnectivityStatus.OFFLINE


class TallyHostValidationError(ValueError):
    pass


def normalize_tally_host(raw: str) -> str:
    host = raw.strip()
    if not host:
        raise TallyHostValidationError("Host / IP address is required.")
    if len(host) > 253:
        raise TallyHostValidationError("Host / IP address is too long.")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    lowered = host.lower().removesuffix(".")
    if not _HOSTNAME_PATTERN.fullmatch(lowered):
        raise TallyHostValidationError(
            "Enter a valid IPv4 address, hostname, or mDNS name (for example LENOVO-TALLY.local).",
        )
    return lowered


def validate_tally_port(raw: str) -> str:
    port = raw.strip()
    if not port.isdigit():
        raise TallyHostValidationError("Port must be a number between 1 and 65535.")
    value = int(port)
    if value < 1 or value > 65535:
        raise TallyHostValidationError("Port must be between 1 and 65535.")
    return str(value)


async def resolve_tally_host(host: str, *, port: str) -> TallyHostResolution:
    configured = normalize_tally_host(host)
    try:
        ipaddress.ip_address(configured)
        logger.info(
            "tally.host.resolved",
            extra={
                "event": "tally.host.resolved",
                "configured_host": configured,
                "resolved_ip": configured,
            },
        )
        return TallyHostResolution(
            configured_host=configured,
            resolved_ip=configured,
            success=True,
            message=f"Using configured IP address {configured}.",
        )
    except ValueError:
        pass

    logger.info(
        "tally.host.resolving",
        extra={"event": "tally.host.resolving", "configured_host": configured, "port": port},
    )
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(
            configured,
            int(port),
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        message = map_resolution_error(configured, exc)
        logger.warning(
            "tally.host.resolve_failed",
            extra={
                "event": "tally.host.resolve_failed",
                "configured_host": configured,
                "error": str(exc),
            },
        )
        return TallyHostResolution(
            configured_host=configured,
            resolved_ip=None,
            success=False,
            message=message,
        )

    if not infos:
        return TallyHostResolution(
            configured_host=configured,
            resolved_ip=None,
            success=False,
            message="The configured host could not be resolved.",
        )

    resolved_ip = infos[0][4][0]
    logger.info(
        "tally.host.resolved",
        extra={
            "event": "tally.host.resolved",
            "configured_host": configured,
            "resolved_ip": resolved_ip,
        },
    )
    return TallyHostResolution(
        configured_host=configured,
        resolved_ip=resolved_ip,
        success=True,
        message=f"Resolved {configured} to {resolved_ip}.",
    )


async def probe_tcp(resolved_ip: str, port: str, *, timeout: float = 5.0) -> tuple[bool, str]:
    logger.info(
        "tally.connection.started",
        extra={"event": "tally.connection.started", "resolved_ip": resolved_ip, "port": port},
    )
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(resolved_ip, int(port)),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
    except TimeoutError:
        logger.warning(
            "tally.connection.timeout",
            extra={"event": "tally.connection.timeout", "resolved_ip": resolved_ip, "port": port},
        )
        return False, "Connection timed out while reaching the Tally workstation."
    except OSError as exc:
        logger.warning(
            "tally.connection.failed",
            extra={
                "event": "tally.connection.failed",
                "resolved_ip": resolved_ip,
                "port": port,
                "error": str(exc),
            },
        )
        return False, map_tcp_error(exc)
    logger.info(
        "tally.connection.successful",
        extra={"event": "tally.connection.successful", "resolved_ip": resolved_ip, "port": port},
    )
    return True, "TCP connection established."


async def probe_xml_server(
    resolved_ip: str, port: str, *, timeout: float = 15.0
) -> tuple[bool, str, str | None, str | None]:
    url = f"http://{resolved_ip}:{port}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                content=_CONNECTION_TEST_XML.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
            )
            response.raise_for_status()
            body = response.text.strip()
    except httpx.TimeoutException:
        logger.warning("tally.xml.timeout", extra={"event": "tally.xml.timeout", "url": url})
        return False, "Tally XML Server did not respond in time.", None, None
    except httpx.HTTPError as exc:
        logger.warning(
            "tally.xml.unavailable",
            extra={"event": "tally.xml.unavailable", "url": url, "error": str(exc)},
        )
        return False, map_http_error(exc), None, None

    if not body:
        return False, "Tally XML Server not enabled.", None, None

    version = _extract_xml_tag(body, ("TALLYVERSION", "VERSION"))
    company = _extract_xml_tag(body, ("SVCURRENTCOMPANY", "COMPANYNAME", "COMPANY"))
    logger.info(
        "tally.xml.responding",
        extra={"event": "tally.xml.responding", "url": url, "tally_version": version},
    )
    return True, "Tally XML Server is responding.", version, company


async def run_connection_diagnostics(
    *,
    host: str,
    port: str,
    expected_company: str | None = None,
) -> TallyConnectionDiagnostics:
    stages: list[TallyConnectionStageResult] = []
    try:
        normalized_port = validate_tally_port(port)
    except TallyHostValidationError as exc:
        return TallyConnectionDiagnostics(
            reachable=False,
            host_resolved=False,
            tcp_connected=False,
            xml_responding=False,
            configured_host=host.strip(),
            resolved_ip=None,
            port=port.strip() or "9000",
            stages=[
                TallyConnectionStageResult(
                    stage=TallyConnectionStage.HOST_RESOLUTION,
                    success=False,
                    message=str(exc),
                ),
            ],
            user_message=str(exc),
            status=TallyConnectivityStatus.CONFIGURATION_ERROR,
        )

    resolution = await resolve_tally_host(host, port=normalized_port)
    stages.append(
        TallyConnectionStageResult(
            stage=TallyConnectionStage.HOST_RESOLUTION,
            success=resolution.success,
            message=resolution.message,
        ),
    )
    if not resolution.success or resolution.resolved_ip is None:
        return TallyConnectionDiagnostics(
            reachable=False,
            host_resolved=False,
            tcp_connected=False,
            xml_responding=False,
            configured_host=resolution.configured_host,
            resolved_ip=None,
            port=normalized_port,
            stages=stages,
            user_message=resolution.message,
            status=TallyConnectivityStatus.OFFLINE,
        )

    tcp_ok, tcp_message = await probe_tcp(resolution.resolved_ip, normalized_port)
    stages.append(
        TallyConnectionStageResult(
            stage=TallyConnectionStage.TCP_CONNECTION,
            success=tcp_ok,
            message=tcp_message,
        ),
    )
    if not tcp_ok:
        return TallyConnectionDiagnostics(
            reachable=False,
            host_resolved=True,
            tcp_connected=False,
            xml_responding=False,
            configured_host=resolution.configured_host,
            resolved_ip=resolution.resolved_ip,
            port=normalized_port,
            stages=stages,
            user_message=tcp_message,
            status=TallyConnectivityStatus.OFFLINE,
        )

    xml_ok, xml_message, version, company = await probe_xml_server(
        resolution.resolved_ip, normalized_port
    )
    stages.append(
        TallyConnectionStageResult(
            stage=TallyConnectionStage.XML_SERVER,
            success=xml_ok,
            message=xml_message,
        ),
    )
    if not xml_ok:
        return TallyConnectionDiagnostics(
            reachable=False,
            host_resolved=True,
            tcp_connected=True,
            xml_responding=False,
            configured_host=resolution.configured_host,
            resolved_ip=resolution.resolved_ip,
            port=normalized_port,
            stages=stages,
            user_message=xml_message,
            status=TallyConnectivityStatus.XML_ERROR,
        )

    resolved_company = expected_company.strip() if expected_company else company
    user_message = "Connected to Tally workstation."
    if resolved_company:
        user_message = f"Connected to Tally workstation ({resolved_company})."

    return TallyConnectionDiagnostics(
        reachable=True,
        host_resolved=True,
        tcp_connected=True,
        xml_responding=True,
        configured_host=resolution.configured_host,
        resolved_ip=resolution.resolved_ip,
        port=normalized_port,
        tally_version=version,
        company_name=resolved_company,
        stages=stages,
        user_message=user_message,
        status=TallyConnectivityStatus.CONNECTED,
    )


def map_resolution_error(host: str, exc: socket.gaierror) -> str:
    _ = host
    text = str(exc).lower()
    if "nodename nor servname" in text or "name or service not known" in text:
        return "The configured host could not be resolved."
    return "The configured host could not be resolved."


def map_tcp_error(exc: OSError) -> str:
    errno = exc.errno
    if errno in {111, 10061}:
        return "Tally workstation is currently offline."
    if errno in {113, 10065, 10051}:
        return "Unable to connect to the configured Tally workstation."
    if errno in {110, 10060}:
        return "Connection timed out while reaching the Tally workstation."
    return "Unable to connect to the configured Tally workstation."


def map_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.ConnectError):
        return "Unable to connect to the configured Tally workstation."
    if isinstance(exc, httpx.TimeoutException):
        return "Connection timed out while reaching the Tally workstation."
    return "Tally XML Server not enabled."


def map_exception_to_user_message(exc: Exception) -> str:
    if isinstance(exc, TallyHostValidationError):
        return str(exc)
    if isinstance(exc, httpx.HTTPError):
        return map_http_error(exc)
    if isinstance(exc, TimeoutError):
        return "Connection timed out while reaching the Tally workstation."
    if isinstance(exc, OSError):
        return map_tcp_error(exc)
    text = str(exc).lower()
    if "connection refused" in text:
        return "Tally workstation is currently offline."
    if "timeout" in text or "timed out" in text:
        return "Connection timed out while reaching the Tally workstation."
    if "name or service not known" in text or "nodename" in text:
        return "The configured host could not be resolved."
    if "unreachable" in text:
        return "Unable to connect to the configured Tally workstation."
    return "Unable to connect to the configured Tally workstation."


def _extract_xml_tag(xml_text: str, tags: tuple[str, ...]) -> str | None:
    upper = xml_text.upper()
    for tag in tags:
        open_tag = f"<{tag}>"
        close_tag = f"</{tag}>"
        start = upper.find(open_tag)
        if start == -1:
            continue
        start += len(open_tag)
        end = upper.find(close_tag, start)
        if end == -1:
            continue
        value = xml_text[start:end].strip()
        if value:
            return value
    return None
