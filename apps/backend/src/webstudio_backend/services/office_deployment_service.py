"""First-run office deployment wizard — detect, configure, and summarize (M12F)."""

from __future__ import annotations

import json
import platform
import socket
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.network_validation_service import (
    NetworkValidationCheck,
    NetworkValidationService,
    _aggregate_status,
    _migration_status,
    _port_listening,
)
from webstudio_backend.services.startup_orchestrator import (
    _storage_path,
    verify_ai_configuration,
    verify_postgresql,
    verify_storage,
    verify_tally_configuration,
)
from webstudio_backend.services.web_image_scraper import find_public_assets_dir

WEBSTUDIO_SERVICE_NAME = "WEBSTUDIO Server"
POSTGRES_SERVICE_NAME = "postgresql-x64-16"


@dataclass(slots=True)
class IpStrategyRecommendation:
    recommended: str  # static_ip | dhcp_reservation
    label: str
    rationale: str
    alternative: str
    alternative_rationale: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class OfficeDeploymentDetection:
    generated_at: str
    overall_status: str
    checks: list[NetworkValidationCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    ip_strategy: IpStrategyRecommendation | None = None
    server_lan_ip: str = ""
    hostname: str = ""
    data_root: str = ""
    api_port: int = 8000

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "checks": [asdict(check) for check in self.checks],
            "recommendations": self.recommendations,
            "ip_strategy": self.ip_strategy.to_dict() if self.ip_strategy else None,
            "server_lan_ip": self.server_lan_ip,
            "hostname": self.hostname,
            "data_root": self.data_root,
            "api_port": self.api_port,
        }


@dataclass(slots=True)
class OfficeDeploymentApplyResult:
    saved_settings: dict[str, str] = field(default_factory=dict)
    created_directories: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


class OfficeDeploymentService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._system = SystemSettingRepository(session)
        self._network = NetworkValidationService(session, settings)

    async def get_status(self) -> dict[str, Any]:
        completed = await self._system.get_bool("office_deployment_completed", default=False)
        summary_raw = await self._system.get_string("office_deployment_summary")
        completed_at = await self._system.get_string("office_deployment_completed_at")
        summary: dict[str, Any] | None = None
        if summary_raw:
            try:
                summary = json.loads(summary_raw)
            except json.JSONDecodeError:
                summary = None
        return {
            "completed": completed,
            "completed_at": completed_at or None,
            "summary_available": summary is not None,
            "summary": summary,
        }

    async def detect(self, *, mdns_active: bool = False) -> OfficeDeploymentDetection:
        checks: list[NetworkValidationCheck] = []
        recommendations: list[str] = []
        lan_ip = self._network._pick_lan_ip()
        hostname = socket.gethostname()
        data_root = self._resolve_writable_data_root()

        checks.append(
            await self._check_network(lan_ip=lan_ip, hostname=hostname, mdns_active=mdns_active)
        )
        checks.append(await self._check_postgresql())
        checks.append(self._check_windows_service())
        checks.append(self._check_api())
        checks.append(await self._check_backup_path(data_root))
        checks.append(await self._check_image_storage(data_root))
        checks.append(await self._check_ai_provider())
        checks.append(await self._check_tally())
        checks.append(self._check_firewall())
        checks.append(self._check_ports(lan_ip))

        ip_strategy = self._recommend_ip_strategy(mdns_active=mdns_active)
        recommendations.append(
            f"Recommended: {ip_strategy.label} — {ip_strategy.rationale}",
        )
        recommendations.append(
            f"Alternative: {ip_strategy.alternative} — {ip_strategy.alternative_rationale}",
        )

        base_report = await self._network.run_admin_validation(mdns_active=mdns_active)
        recommendations.extend(
            item for item in base_report.recommendations if item not in recommendations
        )

        overall = _aggregate_status(checks)
        return OfficeDeploymentDetection(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=overall,
            checks=checks,
            recommendations=recommendations,
            ip_strategy=ip_strategy,
            server_lan_ip=lan_ip,
            hostname=hostname,
            data_root=str(data_root),
            api_port=self._settings.api_port,
        )

    async def apply_recommended_configuration(
        self,
        *,
        actor_id: int | None = None,
    ) -> OfficeDeploymentApplyResult:
        data_root = self._resolve_writable_data_root()
        result = OfficeDeploymentApplyResult()

        directories = [
            data_root / "backups",
            data_root / "backups" / "config",
            data_root / "exports",
            data_root / "assets" / "product-images",
            data_root / "logs",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            result.created_directories.append(str(directory))

        backup_folder = str(data_root / "backups")
        await self._system.set_value(
            "backup_folder",
            backup_folder,
            value_type=SettingValueType.STRING,
            updated_by_user_id=actor_id,
        )
        result.saved_settings["backup_folder"] = backup_folder
        result.messages.append(f"Backup path set to {backup_folder}")

        image_storage = str(data_root / "assets" / "product-images")
        await self._system.set_value(
            "product_image_storage_path",
            image_storage,
            value_type=SettingValueType.STRING,
            updated_by_user_id=actor_id,
        )
        result.saved_settings["product_image_storage_path"] = image_storage
        result.messages.append(f"Image storage path set to {image_storage}")

        server_url = f"http://{self._network._pick_lan_ip()}:{self._settings.api_port}"
        await self._system.set_value(
            "office_server_url",
            server_url,
            value_type=SettingValueType.STRING,
            updated_by_user_id=actor_id,
        )
        result.saved_settings["office_server_url"] = server_url

        discovery_urls = json.dumps([server_url])
        await self._system.set_value(
            "office_discovery_urls",
            discovery_urls,
            value_type=SettingValueType.JSON,
            updated_by_user_id=actor_id,
        )
        result.saved_settings["office_discovery_urls"] = discovery_urls
        result.messages.append(f"Client connection URL recorded: {server_url}")

        tally_enabled = await self._system.get_bool("tally_enabled", default=False)
        if tally_enabled:
            host = (await self._system.get_string("tally_host") or "").strip()
            if not host or host in {"127.0.0.1", "localhost"}:
                result.messages.append(
                    "Tally host still localhost — set the Tally laptop hostname in Settings → Tally after deployment.",
                )

        return result

    async def build_deployment_summary(
        self,
        detection: OfficeDeploymentDetection,
        apply_result: OfficeDeploymentApplyResult | None = None,
    ) -> dict[str, Any]:
        company = (await self._system.get_string("company_name") or "").strip()
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "company_name": company,
            "overall_status": detection.overall_status,
            "server_lan_ip": detection.server_lan_ip,
            "hostname": detection.hostname,
            "data_root": detection.data_root,
            "api_port": detection.api_port,
            "ip_strategy": detection.ip_strategy.to_dict() if detection.ip_strategy else None,
            "checks": [asdict(check) for check in detection.checks],
            "recommendations": detection.recommendations,
            "saved_configuration": apply_result.saved_settings if apply_result else {},
            "created_directories": apply_result.created_directories if apply_result else [],
            "apply_messages": apply_result.messages if apply_result else [],
            "client_connection_url": (
                apply_result.saved_settings.get("office_server_url") if apply_result else None
            ),
            "configuration_files_required": False,
            "administrator_note": (
                "All paths and connection hints were saved in WEBSTUDIO system settings. "
                "No manual .env or config file editing is required for standard office deployment."
            ),
        }

    async def complete_deployment(
        self,
        *,
        mdns_active: bool = False,
        actor_id: int | None = None,
    ) -> tuple[OfficeDeploymentDetection, OfficeDeploymentApplyResult, dict[str, Any]]:
        detection = await self.detect(mdns_active=mdns_active)
        apply_result = await self.apply_recommended_configuration(actor_id=actor_id)
        summary = await self.build_deployment_summary(detection, apply_result)

        await self._system.set_value(
            "office_deployment_summary",
            json.dumps(summary),
            value_type=SettingValueType.JSON,
            updated_by_user_id=actor_id,
        )
        await self._system.set_value(
            "office_deployment_completed",
            "true",
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=actor_id,
        )
        await self._system.set_value(
            "office_deployment_completed_at",
            datetime.now(UTC).isoformat(),
            value_type=SettingValueType.STRING,
            updated_by_user_id=actor_id,
        )

        return detection, apply_result, summary

    async def _check_network(
        self,
        *,
        lan_ip: str,
        hostname: str,
        mdns_active: bool,
    ) -> NetworkValidationCheck:
        detail = (
            f"Hostname {hostname}; LAN IP {lan_ip}; mDNS {'active' if mdns_active else 'inactive'}"
        )
        status = "passed"
        message = "Office LAN connectivity detected"
        if lan_ip.startswith("127."):
            status = "warning"
            message = "Server appears to use loopback only — verify LAN adapter is active"
        return NetworkValidationCheck(
            key="network",
            name="Network",
            status=status,
            message=message,
            detail=detail,
        )

    async def _check_postgresql(self) -> NetworkValidationCheck:
        pg = await verify_postgresql(self._settings)
        mig_status, mig_msg = await _migration_status(self._session)
        pg_service = self._query_windows_service(POSTGRES_SERVICE_NAME)
        detail_parts = [mig_msg]
        if pg_service:
            detail_parts.append(pg_service)
        status = "passed" if pg.status == "ok" and mig_status == "passed" else "failed"
        return NetworkValidationCheck(
            key="postgresql",
            name="PostgreSQL",
            status=status,
            message=pg.detail or pg.status,
            detail="; ".join(detail_parts),
        )

    def _check_windows_service(self) -> NetworkValidationCheck:
        service_state = self._query_windows_service(WEBSTUDIO_SERVICE_NAME)
        if platform.system() != "Windows":
            return NetworkValidationCheck(
                key="windows_service",
                name="Windows Service",
                status="skipped",
                message="Development / non-Windows host — service check skipped",
                detail="Production servers run WEBSTUDIO Server via NSSM on Windows.",
            )
        if service_state is None:
            return NetworkValidationCheck(
                key="windows_service",
                name="Windows Service",
                status="warning",
                message=f"{WEBSTUDIO_SERVICE_NAME} not installed",
                detail="Run infra/windows/install-webstudio-service.ps1 on the server PC.",
            )
        running = "RUNNING" in service_state.upper()
        return NetworkValidationCheck(
            key="windows_service",
            name="Windows Service",
            status="passed" if running else "warning",
            message=f"{WEBSTUDIO_SERVICE_NAME} {'running' if running else 'installed but not running'}",
            detail=service_state,
        )

    def _check_api(self) -> NetworkValidationCheck:
        api_ok = _port_listening("127.0.0.1", self._settings.api_port)
        return NetworkValidationCheck(
            key="api",
            name="API",
            status="passed" if api_ok else "failed",
            message=f"Port {self._settings.api_port} {'listening' if api_ok else 'not reachable'}",
            detail=f"Environment: {self._settings.app_env}",
        )

    async def _check_backup_path(self, data_root: Path) -> NetworkValidationCheck:
        backup_folder = await self._system.get_string("backup_folder") or "backups"
        backup_path = Path(backup_folder)
        if not backup_path.is_absolute():
            backup_path = data_root / backup_folder
        writable = self._probe_writable(backup_path)
        storage = await verify_storage(self._settings)
        status = "passed" if writable and storage.status == "ok" else "warning"
        return NetworkValidationCheck(
            key="backup_path",
            name="Backup Path",
            status=status,
            message=str(backup_path),
            detail=(
                storage.detail if storage.status != "ok" else "Writable backup directory confirmed"
            ),
        )

    async def _check_image_storage(self, data_root: Path) -> NetworkValidationCheck:
        configured = await self._system.get_string("product_image_storage_path")
        assets_dir = find_public_assets_dir()
        if configured:
            target = Path(configured)
        elif assets_dir is not None:
            target = assets_dir
        else:
            target = data_root / "assets" / "product-images"
        writable = self._probe_writable(target)
        return NetworkValidationCheck(
            key="image_storage",
            name="Image Storage",
            status="passed" if writable else "warning",
            message=str(target),
            detail="Product image uploads and scraped assets storage",
        )

    async def _check_ai_provider(self) -> NetworkValidationCheck:
        ai = await verify_ai_configuration(self._session, self._settings)
        status_map = {"ok": "passed", "warning": "warning", "failed": "failed"}
        return NetworkValidationCheck(
            key="ai_provider",
            name="AI Provider",
            status=status_map.get(ai.status, "warning"),
            message=ai.detail or "AI configuration checked",
        )

    async def _check_tally(self) -> NetworkValidationCheck:
        tally_cfg = await verify_tally_configuration(self._session)
        tally_enabled = await self._system.get_bool("tally_enabled", default=False)
        if not tally_enabled:
            return NetworkValidationCheck(
                key="tally",
                name="Tally",
                status="skipped",
                message="Tally integration disabled",
                detail="Enable in Settings → Tally after billing PC is on the LAN.",
            )
        tally_status = tally_cfg.status
        tally_detail = tally_cfg.detail
        if tally_enabled:
            from webstudio_backend.services.tally_connectivity_service import (
                TallyConnectivityService,
            )

            try:
                diagnostics = await TallyConnectivityService(self._session).test_connection()
                if diagnostics.reachable:
                    tally_status = "passed"
                    tally_detail = diagnostics.user_message or "Workstation reachable."
                else:
                    tally_status = "warning"
                    tally_detail = diagnostics.user_message or "Tally workstation offline."
            except Exception as exc:
                tally_status = "warning"
                tally_detail = str(exc)
        status_map = {"ok": "passed", "warning": "warning", "failed": "failed"}
        mapped = status_map.get(tally_status, tally_status)
        return NetworkValidationCheck(
            key="tally",
            name="Tally",
            status=mapped if mapped in {"passed", "warning", "failed", "skipped"} else "warning",
            message=tally_detail or "Tally configuration checked",
        )

    def _check_firewall(self) -> NetworkValidationCheck:
        pg_local = _port_listening("127.0.0.1", 5432)
        return NetworkValidationCheck(
            key="firewall",
            name="Firewall",
            status="warning",
            message="Confirm Windows Firewall allows LAN clients to reach the API port",
            detail=(
                f"Run infra/windows/configure-firewall.ps1. "
                f"PostgreSQL 5432 {'localhost only' if pg_local else 'check binding'}."
            ),
        )

    def _check_ports(self, lan_ip: str) -> NetworkValidationCheck:
        api_ok = _port_listening("127.0.0.1", self._settings.api_port)
        tally_port = 9000
        lines = [
            f"API TCP {self._settings.api_port} (server {lan_ip})",
            "PostgreSQL TCP 5432 (localhost)",
            "mDNS UDP 5353 (client discovery)",
            f"Tally TCP {tally_port} (server → billing laptop)",
        ]
        return NetworkValidationCheck(
            key="ports",
            name="Ports",
            status="passed" if api_ok else "warning",
            message="; ".join(lines),
        )

    @staticmethod
    def _recommend_ip_strategy(*, mdns_active: bool) -> IpStrategyRecommendation:
        if mdns_active:
            return IpStrategyRecommendation(
                recommended="dhcp_reservation",
                label="DHCP Reservation",
                rationale=(
                    "Reserve the server PC MAC address in your router so the LAN IP stays stable. "
                    "mDNS is active for client discovery on the same subnet."
                ),
                alternative="Static IP",
                alternative_rationale=(
                    "Assign a fixed IP on the server network adapter if your router does not support reservations."
                ),
            )
        return IpStrategyRecommendation(
            recommended="static_ip",
            label="Static IP",
            rationale=(
                "Assign a fixed LAN IP on the dedicated server PC (or router DHCP reservation) because "
                "mDNS is not currently advertising — clients need a stable address."
            ),
            alternative="DHCP Reservation",
            alternative_rationale=(
                "Router MAC reservation achieves the same stability without configuring the server adapter manually."
            ),
        )

    @staticmethod
    def _resolve_writable_data_root() -> Path:
        from webstudio_backend.core.config import get_settings

        settings = get_settings()
        data_root = _storage_path(settings)
        if str(data_root) not in {"/", ""} and OfficeDeploymentService._probe_writable(data_root):
            return data_root
        fallback = Path.cwd() / "webstudio-data"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    @staticmethod
    def _probe_writable(path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    @staticmethod
    def _query_windows_service(service_name: str) -> str | None:
        if platform.system() != "Windows":
            return None
        try:
            completed = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        output = completed.stdout.strip()
        return output.splitlines()[0] if output else service_name
