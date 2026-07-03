"""Enterprise network validation for administrator wizard (M12D, M14B)."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.discovery_health_service import build_discovery_health_payload
from webstudio_backend.services.startup_orchestrator import (
    _storage_path,
    verify_ai_configuration,
    verify_configuration,
    verify_postgresql,
    verify_storage,
    verify_tally_configuration,
)
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService


@dataclass(frozen=True, slots=True)
class NetworkValidationCheck:
    key: str
    name: str
    status: str  # passed | warning | failed | skipped
    message: str
    detail: str = ""


@dataclass(slots=True)
class NetworkValidationReport:
    generated_at: str
    overall_status: str
    topology: str
    checks: list[NetworkValidationCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "topology": self.topology,
            "checks": [asdict(check) for check in self.checks],
            "recommendations": self.recommendations,
        }


OFFICE_TOPOLOGY = (
    "Ground Floor → Access Point → LAN → First Floor Router → "
    "Dedicated Server PC → Desktop / Android / iPhone clients; "
    "movable Tally laptop on same LAN (multiple SSIDs / DHCP reservation supported)."
)

PRODUCTION_MULTI_SSID_GUIDANCE = (
    "Use the same LAN/VLAN for all store Wi‑Fi SSIDs and access points; disable client "
    "isolation on APs; prefer DHCP reservation or static IP for the server; document "
    "candidate URLs in Office Deployment so clients reconnect after AP roaming."
)

PRODUCTION_INFRASTRUCTURE_CHECKLIST: list[dict[str, str]] = [
    {"id": "NET-01", "item": "Server has static IP or DHCP reservation", "owner": "IT"},
    {"id": "NET-02", "item": "API port reachable from LAN subnet", "owner": "IT"},
    {"id": "NET-03", "item": "All store SSIDs route to same subnet/VLAN", "owner": "IT"},
    {"id": "NET-04", "item": "Windows Firewall allows API + mDNS from store subnet", "owner": "IT"},
    {"id": "NET-05", "item": "PostgreSQL bound to localhost only (port 5432)", "owner": "IT"},
    {"id": "NET-06", "item": "Desktop client connects via discovery or saved URL", "owner": "Store admin"},
    {"id": "NET-07", "item": "Android client connects on store Wi‑Fi", "owner": "Store admin"},
    {"id": "NET-08", "item": "iOS client connects on store Wi‑Fi", "owner": "Store admin"},
    {"id": "NET-09", "item": "Client auto-reconnect verified after server restart", "owner": "Store admin"},
    {"id": "NET-10", "item": "Tally laptop hostname resolves from server (if enabled)", "owner": "Accounts"},
]


def _port_listening(host: str, port: int, *, udp: bool = False) -> bool:
    sock_type = socket.SOCK_DGRAM if udp else socket.SOCK_STREAM
    probe = socket.socket(socket.AF_INET, sock_type)
    probe.settimeout(1.5)
    try:
        if udp:
            probe.sendto(b"\x00", (host, port))
            return True
        result = probe.connect_ex((host, port))
        return result == 0
    except OSError:
        return False
    finally:
        probe.close()


async def _migration_status(session: AsyncSession) -> tuple[str, str]:
    try:
        result = await session.execute(text("SELECT version_num FROM webstudio.alembic_version"))
        current = result.scalar_one_or_none()
        if current is None:
            return "failed", "Alembic version table is empty."
        return "passed", f"Schema revision {current}."
    except Exception as exc:
        return "failed", f"Could not read migration version: {exc}"


async def _http_probe(url: str, *, timeout: float = 2.5) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code < 500:
                return True, f"HTTP {response.status_code}"
            return False, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)


def _lan_base_url(settings: Settings, lan_ip: str) -> str:
    host = lan_ip if lan_ip and lan_ip != "127.0.0.1" else "127.0.0.1"
    return f"http://{host}:{settings.api_port}"


async def _load_office_discovery_urls(system: SystemSettingRepository) -> list[str]:
    stored_raw = await system.get_string("office_discovery_urls")
    if not stored_raw:
        return []
    try:
        parsed = json.loads(stored_raw)
        if isinstance(parsed, list):
            return [str(item).rstrip("/") for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        return []
    return []


def _ip_documented_for_clients(
    lan_ip: str,
    *,
    office_urls: list[str],
    discovery_candidates: list[str],
) -> bool:
    if not lan_ip or lan_ip == "127.0.0.1":
        return False
    needle = lan_ip.lower()
    for candidate in [*office_urls, *discovery_candidates]:
        if needle in candidate.lower():
            return True
    return False


def _same_subnet_hint(lan_ip: str) -> str:
    octets = lan_ip.split(".")
    if len(octets) == 4 and all(part.isdigit() for part in octets):
        return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
    return "office LAN subnet"


class NetworkValidationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._system = SystemSettingRepository(session)

    async def run_admin_validation(self, *, mdns_active: bool = False) -> NetworkValidationReport:
        checks: list[NetworkValidationCheck] = []
        recommendations: list[str] = []

        # Server
        lan_ip = self._pick_lan_ip()
        checks.append(
            NetworkValidationCheck(
                key="server",
                name="Server",
                status="passed",
                message=f"API bound to {self._settings.api_host}:{self._settings.api_port}",
                detail=f"LAN IP {lan_ip}; mDNS {'active' if mdns_active else 'inactive'}",
            ),
        )
        if not mdns_active and self._settings.mdns_enabled:
            checks[-1] = NetworkValidationCheck(
                key="server",
                name="Server",
                status="warning",
                message="mDNS advertisement is enabled but not running.",
                detail="Clients on other subnets may need a saved hostname or static IP.",
            )
            recommendations.append(
                "Enable mDNS reflector on routers if clients use multiple Wi‑Fi SSIDs on the same LAN.",
            )

        # Database
        pg = await verify_postgresql(self._settings)
        mig_status, mig_msg = await _migration_status(self._session)
        db_status = "passed" if pg.status == "ok" and mig_status == "passed" else "failed"
        checks.append(
            NetworkValidationCheck(
                key="database",
                name="Database",
                status=db_status,
                message=pg.detail or pg.status,
                detail=mig_msg,
            ),
        )

        # API
        api_ok = _port_listening("127.0.0.1", self._settings.api_port)
        checks.append(
            NetworkValidationCheck(
                key="api",
                name="API",
                status="passed" if api_ok else "failed",
                message=f"Port {self._settings.api_port} {'listening' if api_ok else 'not reachable locally'}",
                detail=f"Environment: {self._settings.app_env}",
            ),
        )

        # Firewall (local bind probe — rules must allow LAN clients)
        pg_local = _port_listening("127.0.0.1", 5432)
        checks.append(
            NetworkValidationCheck(
                key="firewall",
                name="Firewall",
                status="warning",
                message="Verify Windows Firewall allows inbound API port from store subnet.",
                detail=(
                    f"Local PostgreSQL port 5432 {'open on localhost' if pg_local else 'not detected'}; "
                    "run infra/windows/configure-firewall.ps1 on the server."
                ),
            ),
        )

        # Ports
        tally_host, tally_port, _ = await self._tally_endpoints()
        tally_port_int = int(tally_port) if tally_port.isdigit() else 9000
        port_lines = [
            f"API {self._settings.api_port}",
            f"PostgreSQL 5432 ({'localhost' if pg_local else 'check'})",
            "mDNS UDP 5353 (client discovery)",
            f"Tally {tally_port_int} (server → laptop)",
        ]
        checks.append(
            NetworkValidationCheck(
                key="ports",
                name="Ports",
                status="passed" if api_ok else "warning",
                message="; ".join(port_lines),
            ),
        )

        # AI
        ai = await verify_ai_configuration(self._session, self._settings)
        ai_config = await resolve_ai_config(self._session, self._settings)
        ai_status = {"ok": "passed", "warning": "warning", "failed": "failed"}.get(ai.status, "warning")
        checks.append(
            NetworkValidationCheck(
                key="ai",
                name="AI",
                status=ai_status,
                message=ai.detail or ai_config.primary_provider,
            ),
        )

        # Tally
        tally_cfg = await verify_tally_configuration(self._session)
        tally_enabled = await self._system.get_bool("tally_enabled", default=False)
        tally_status = tally_cfg.status
        tally_detail = tally_cfg.detail
        if tally_enabled:
            try:
                diagnostics = await TallyConnectivityService(self._session).test_connection()
                await self._session.commit()
                if diagnostics.reachable:
                    tally_status = "passed"
                    tally_detail = diagnostics.user_message or "Workstation reachable."
                else:
                    tally_status = "warning"
                    tally_detail = diagnostics.user_message or "Tally workstation offline — sync will retry automatically."
                    recommendations.append(
                        "Tally laptop may be on another floor or SSID; ensure hostname resolves and TCP "
                        f"{tally_port_int} is open on the laptop when Tally is running.",
                    )
            except Exception as exc:
                tally_status = "warning"
                tally_detail = str(exc)
        checks.append(
            NetworkValidationCheck(
                key="tally",
                name="Tally",
                status="skipped" if not tally_enabled else tally_status,
                message=tally_detail if tally_enabled else "Tally integration disabled",
            ),
        )

        # Backup folders
        backup_folder = await self._system.get_string("backup_folder") or str(
            Path(self._settings.webstudio_data_root or ".") / "backups",
        )
        backup_path = Path(backup_folder)
        backup_ok = backup_path.exists() and backup_path.is_dir()
        try:
            test_file = backup_path / ".write_probe"
            backup_path.mkdir(parents=True, exist_ok=True)
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            writable = True
        except OSError:
            writable = False
        storage = await verify_storage(self._settings)
        checks.append(
            NetworkValidationCheck(
                key="backup_folders",
                name="Backup folders",
                status="passed" if backup_ok and writable and storage.status == "ok" else "warning",
                message=str(backup_path),
                detail=storage.detail,
            ),
        )

        config = await verify_configuration(self._session, self._settings)
        if config.status == "warning":
            recommendations.append(config.detail)

        overall = _aggregate_status(checks)
        return NetworkValidationReport(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=overall,
            topology=OFFICE_TOPOLOGY,
            checks=checks,
            recommendations=recommendations,
        )

    async def run_production_network_validation(
        self,
        *,
        mdns_active: bool = False,
    ) -> NetworkValidationReport:
        """Production networking validation for M14B commissioning."""
        checks: list[NetworkValidationCheck] = []
        recommendations: list[str] = []
        lan_ip = self._pick_lan_ip()
        api_port = self._settings.api_port
        office_urls = await _load_office_discovery_urls(self._system)
        discovery_candidates = list(
            dict.fromkeys([*office_urls, *self._settings.discovery_candidate_urls()]),
        )
        lan_base = _lan_base_url(self._settings, lan_ip)
        subnet_hint = _same_subnet_hint(lan_ip)
        localhost_api = _port_listening("127.0.0.1", api_port)
        lan_api_socket = _port_listening(lan_ip, api_port) if lan_ip != "127.0.0.1" else localhost_api

        # Static server IP
        ip_documented = _ip_documented_for_clients(
            lan_ip,
            office_urls=office_urls,
            discovery_candidates=discovery_candidates,
        )
        static_status = "passed" if ip_documented else "warning"
        static_message = (
            f"Server LAN IP {lan_ip} documented in discovery candidates."
            if ip_documented
            else f"Server LAN IP {lan_ip} is not listed in office discovery settings."
        )
        checks.append(
            NetworkValidationCheck(
                key="static_server_ip",
                name="Static server IP",
                status=static_status,
                message=static_message,
                detail="Assign a DHCP reservation or static IP and record it in Office Deployment.",
            ),
        )
        if not ip_documented:
            recommendations.append(
                "Document the server IP via Office Deployment wizard or WEBSTUDIO_DISCOVERY_CANDIDATES.",
            )

        # LAN accessibility
        lan_http_ok, lan_http_detail = await _http_probe(urljoin(lan_base, "/api/v1/health/live"))
        lan_status = "passed" if lan_api_socket and lan_http_ok else "failed"
        if localhost_api and not lan_api_socket and self._settings.api_host not in {"0.0.0.0", "::"}:
            lan_status = "failed"
        checks.append(
            NetworkValidationCheck(
                key="lan_accessibility",
                name="LAN accessibility",
                status=lan_status,
                message=(
                    f"API reachable at {lan_base} from server ({lan_http_detail})."
                    if lan_http_ok
                    else f"API not reachable on LAN at {lan_base}."
                ),
                detail=f"Bind host: {self._settings.api_host}; socket probe: {'ok' if lan_api_socket else 'failed'}.",
            ),
        )

        # Multiple Wi‑Fi access points
        multi_ap_status = "passed" if mdns_active or discovery_candidates else "warning"
        checks.append(
            NetworkValidationCheck(
                key="multi_wifi_access_points",
                name="Multiple Wi‑Fi access points",
                status=multi_ap_status,
                message=(
                    "Discovery candidates configured for multi-SSID roaming."
                    if discovery_candidates
                    else "Configure discovery candidates for multi-AP offices."
                ),
                detail=PRODUCTION_MULTI_SSID_GUIDANCE,
            ),
        )

        # Same subnet communication
        binds_lan = self._settings.api_host in {"0.0.0.0", "::", lan_ip}
        same_subnet_status = "passed" if binds_lan and lan_ip != "127.0.0.1" else "warning"
        checks.append(
            NetworkValidationCheck(
                key="same_subnet_communication",
                name="Same subnet communication",
                status=same_subnet_status,
                message=f"Server advertises on {subnet_hint} at {lan_ip}:{api_port}.",
                detail="Clients on store Wi‑Fi must share the same routed subnet/VLAN as the server.",
            ),
        )

        # Windows Firewall
        firewall_status = "passed"
        firewall_message = f"Inbound API port {api_port} reachable on LAN interface."
        if localhost_api and not lan_api_socket and lan_ip != "127.0.0.1":
            firewall_status = "failed"
            firewall_message = (
                f"API listens locally but not on LAN IP {lan_ip} — check Windows Firewall and bind host."
            )
            recommendations.append(
                f"Run infra/windows/configure-firewall.ps1 -ApiPort {api_port} -Subnet {subnet_hint}.",
            )
        elif not localhost_api:
            firewall_status = "failed"
            firewall_message = f"API port {api_port} is not listening."
        checks.append(
            NetworkValidationCheck(
                key="windows_firewall",
                name="Windows Firewall",
                status=firewall_status,
                message=firewall_message,
                detail="PostgreSQL must remain localhost-only; API and mDNS are LAN inbound.",
            ),
        )

        # Port availability
        pg_local = _port_listening("127.0.0.1", 5432)
        mdns_udp = _port_listening("127.0.0.1", 5353, udp=True)
        port_status = "passed" if localhost_api and pg_local else "failed"
        checks.append(
            NetworkValidationCheck(
                key="port_availability",
                name="Port availability",
                status=port_status,
                message=(
                    f"API {api_port}, PostgreSQL 5432 (localhost), mDNS UDP 5353 "
                    f"({'active' if mdns_udp else 'not probed'})."
                ),
                detail="Tally TCP 9000 is outbound from server to billing laptop.",
            ),
        )

        # PostgreSQL connectivity
        pg = await verify_postgresql(self._settings)
        mig_status, mig_msg = await _migration_status(self._session)
        pg_status = "passed" if pg.status == "ok" and mig_status == "passed" and pg_local else "failed"
        checks.append(
            NetworkValidationCheck(
                key="postgresql_connectivity",
                name="PostgreSQL connectivity",
                status=pg_status,
                message=pg.detail or pg.status,
                detail=f"{mig_msg} Localhost-only: {'yes' if pg_local else 'verify bind'}",
            ),
        )

        # API reachability
        local_http_ok, local_http_detail = await _http_probe(
            urljoin(_lan_base_url(self._settings, "127.0.0.1"), "/api/v1/health/live"),
        )
        api_status = "passed" if localhost_api and local_http_ok else "failed"
        checks.append(
            NetworkValidationCheck(
                key="api_reachability",
                name="API reachability",
                status=api_status,
                message=f"Local: {local_http_detail}; LAN: {lan_http_detail}.",
                detail=f"Environment: {self._settings.app_env}",
            ),
        )

        # Server discovery
        discovery_payload = await build_discovery_health_payload(self._session, self._settings)
        discovery_online = bool(discovery_payload.get("online"))
        discovery_status = "passed" if discovery_online and (mdns_active or discovery_candidates) else "warning"
        if self._settings.mdns_enabled and not mdns_active:
            discovery_status = "warning"
            recommendations.append("Start mDNS advertisement or provide manual discovery URLs for clients.")
        checks.append(
            NetworkValidationCheck(
                key="server_discovery",
                name="Server discovery",
                status=discovery_status,
                message=(
                    f"mDNS {'active' if mdns_active else 'inactive'}; "
                    f"{len(discovery_candidates)} discovery candidate URL(s)."
                ),
                detail=f"Service type: {discovery_payload.get('service_type')}",
            ),
        )

        # Client platform connectivity (server-side endpoint probes)
        desktop_ok = lan_http_ok and local_http_ok
        checks.append(
            NetworkValidationCheck(
                key="desktop_connectivity",
                name="Desktop connectivity",
                status="passed" if desktop_ok else "failed",
                message=(
                    "Desktop clients can reach /api/v1/health/live on the LAN base URL."
                    if desktop_ok
                    else "Desktop clients cannot reach the API — verify LAN URL and firewall."
                ),
                detail="Validate on a staff desktop: Settings → Network wizard or Connection diagnostics.",
            ),
        )

        for platform_key, platform_name, platform_id in (
            ("android_connectivity", "Android connectivity", "mobile_android"),
            ("ios_connectivity", "iOS connectivity", "mobile_ios"),
        ):
            mobile_url = (
                f"{lan_base}/api/v1/client-updates/check"
                f"?platform={platform_id}&current_version=0.0.0"
            )
            mobile_ok, mobile_detail = await _http_probe(mobile_url)
            checks.append(
                NetworkValidationCheck(
                    key=platform_key,
                    name=platform_name,
                    status="passed" if mobile_ok and lan_http_ok else "failed",
                    message=f"{platform_name} endpoint probe: {mobile_detail}.",
                    detail="On-device test: open app on store Wi‑Fi and confirm server discovery or saved URL.",
                ),
            )

        # Automatic reconnect
        reconnect_status = "passed" if discovery_online and discovery_candidates else "warning"
        checks.append(
            NetworkValidationCheck(
                key="automatic_reconnect",
                name="Automatic reconnect",
                status=reconnect_status,
                message=(
                    "Discovery health online with candidate URLs for client auto-reconnect."
                    if reconnect_status == "passed"
                    else "Configure discovery candidates and verify clients after a server restart."
                ),
                detail=(
                    "Desktop polls saved URLs and discovery candidates (M12D ConnectionReconnectService); "
                    "mobile clients use the same LAN discovery endpoints."
                ),
            ),
        )

        config = await verify_configuration(self._session, self._settings)
        if config.status == "warning":
            recommendations.append(config.detail)

        overall = _aggregate_status(checks)
        return NetworkValidationReport(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=overall,
            topology=OFFICE_TOPOLOGY,
            checks=checks,
            recommendations=recommendations,
        )

    async def build_production_network_report(self, *, mdns_active: bool = False) -> dict[str, object]:
        validation = await self.run_production_network_validation(mdns_active=mdns_active)
        data_root = _storage_path(self._settings)
        lan_ip = self._pick_lan_ip()
        office_urls = await _load_office_discovery_urls(self._system)
        discovery_candidates = list(
            dict.fromkeys([*office_urls, *self._settings.discovery_candidate_urls()]),
        )
        return {
            **validation.to_dict(),
            "validation_scope": "production",
            "server_lan_ip": lan_ip,
            "mdns_enabled": self._settings.mdns_enabled,
            "mdns_active": mdns_active,
            "discovery_candidates": discovery_candidates,
            "api_port": self._settings.api_port,
            "api_bind_host": self._settings.api_host,
            "data_root": str(data_root),
            "multi_ssid_guidance": PRODUCTION_MULTI_SSID_GUIDANCE,
            "infrastructure_checklist": PRODUCTION_INFRASTRUCTURE_CHECKLIST,
            "firewall_script": "infra/windows/configure-firewall.ps1",
            "validation_script": "infra/windows/validate-production-network.ps1",
        }

    async def build_network_report(self, *, mdns_active: bool = False) -> dict[str, object]:
        validation = await self.run_admin_validation(mdns_active=mdns_active)
        data_root = _storage_path(self._settings)
        return {
            **validation.to_dict(),
            "server_lan_ip": self._pick_lan_ip(),
            "mdns_enabled": self._settings.mdns_enabled,
            "mdns_active": mdns_active,
            "discovery_candidates": self._settings.discovery_candidate_urls(),
            "api_port": self._settings.api_port,
            "data_root": str(data_root),
            "multi_ssid_guidance": (
                "Use the same LAN/VLAN for all store SSIDs; prefer hostname + DHCP reservation "
                "for the server and Tally laptop; clients auto-reconnect without manual steps."
            ),
        }

    async def _tally_endpoints(self) -> tuple[str, str, str]:
        host = (await self._system.get_string("tally_host") or "127.0.0.1").strip()
        port = (await self._system.get_string("tally_port") or "9000").strip()
        company = (await self._system.get_string("tally_company_name") or "").strip()
        return host, port, company

    @staticmethod
    def _pick_lan_ip() -> str:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            address = probe.getsockname()[0]
            probe.close()
            return address
        except OSError:
            return "127.0.0.1"


def _aggregate_status(checks: list[NetworkValidationCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"
