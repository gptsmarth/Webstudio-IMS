"""Tally connectivity orchestration — health persistence and API payloads."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.integrations.tally.connectivity import (
    TallyConnectionDiagnostics,
    TallyConnectivityStatus,
    TallyHostValidationError,
    normalize_tally_host,
    run_connection_diagnostics,
    validate_tally_port,
)
from webstudio_backend.integrations.tally.xml_client import TallyXmlClient

logger = logging.getLogger(__name__)


class TallyConnectivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._company_sync = TallyCompanySyncRepository(session)

    async def get_config(self) -> tuple[str, str, str]:
        host = (await self._settings.get_string("tally_host") or "127.0.0.1").strip()
        port = (await self._settings.get_string("tally_port") or "9000").strip()
        company = (await self._settings.get_string("tally_company_name") or "WEBSTUDIO").strip()
        return host, port, company

    async def validate_configuration(self, host: str, port: str) -> None:
        normalize_tally_host(host)
        validate_tally_port(port)

    async def test_connection(self) -> TallyConnectionDiagnostics:
        host, port, company = await self.get_config()
        diagnostics = await run_connection_diagnostics(
            host=host, port=port, expected_company=company
        )
        await self._persist_diagnostics(company, diagnostics)
        return diagnostics

    async def ensure_workstation_reachable(
        self, *, company_name: str
    ) -> TallyConnectionDiagnostics:
        host, port, configured_company = await self.get_config()
        resolved_company = company_name or configured_company
        diagnostics = await run_connection_diagnostics(
            host=host,
            port=port,
            expected_company=resolved_company,
        )
        await self._persist_diagnostics(resolved_company, diagnostics)
        if not diagnostics.reachable:
            logger.warning(
                "tally.sync.workstation_offline",
                extra={
                    "event": "tally.sync.workstation_offline",
                    "configured_host": diagnostics.configured_host,
                    "resolved_ip": diagnostics.resolved_ip,
                    "user_message": diagnostics.user_message,
                },
            )
        return diagnostics

    async def build_client_for_sync(
        self, diagnostics: TallyConnectionDiagnostics, *, timeout: float | None = None
    ) -> TallyXmlClient:
        if not diagnostics.reachable or diagnostics.resolved_ip is None:
            raise TallyHostValidationError(diagnostics.user_message)
        if timeout is None:
            return TallyXmlClient(diagnostics.resolved_ip, diagnostics.port)
        return TallyXmlClient(diagnostics.resolved_ip, diagnostics.port, timeout=timeout)

    async def build_health_payload(self) -> dict[str, object]:
        host, port, company_name = await self.get_config()
        enabled_raw = await self._settings.get_string("tally_enabled")
        enabled = (enabled_raw or "false").strip().lower() in {"1", "true", "yes"}
        company_sync = await self._company_sync.get_or_create(company_name)

        status = company_sync.connectivity_status or TallyConnectivityStatus.OFFLINE.value
        if not enabled:
            status = TallyConnectivityStatus.OFFLINE.value

        return {
            "enabled": enabled,
            "status": status,
            "configured_host": host,
            "port": port,
            "company_name": company_name,
            "resolved_ip": company_sync.last_resolved_ip,
            "connection_status": company_sync.connection_status,
            "last_successful_sync_at": (
                company_sync.last_successful_sync_at.isoformat()
                if company_sync.last_successful_sync_at
                else None
            ),
            "last_successful_connection_at": (
                company_sync.last_successful_connection_at.isoformat()
                if company_sync.last_successful_connection_at
                else None
            ),
            "last_failed_connection_at": (
                company_sync.last_failed_connection_at.isoformat()
                if company_sync.last_failed_connection_at
                else None
            ),
            "last_failure_reason": company_sync.last_error,
            "waiting_for_workstation": status
            in {
                TallyConnectivityStatus.OFFLINE.value,
                TallyConnectivityStatus.XML_ERROR.value,
            }
            and enabled,
            "user_message": company_sync.last_error or _status_message(status, enabled),
        }

    async def _persist_diagnostics(
        self, company_name: str, diagnostics: TallyConnectionDiagnostics
    ) -> None:
        company_sync = await self._company_sync.get_or_create(company_name)
        now = datetime.now(UTC)
        if diagnostics.reachable:
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="connected",
                connectivity_status=diagnostics.status.value,
                last_error="",
                last_successful_connection_at=now,
                last_resolved_ip=diagnostics.resolved_ip,
            )
            return

        await self._company_sync.update_sync_state(
            company_sync,
            connection_status="disconnected" if diagnostics.tcp_connected else "error",
            connectivity_status=diagnostics.status.value,
            last_error=diagnostics.user_message,
            last_failed_connection_at=now,
            last_resolved_ip=diagnostics.resolved_ip,
        )

    @staticmethod
    def diagnostics_to_api(diagnostics: TallyConnectionDiagnostics) -> dict[str, object]:
        return {
            "connected": diagnostics.reachable,
            "reachable": diagnostics.reachable,
            "host_resolved": diagnostics.host_resolved,
            "tcp_connected": diagnostics.tcp_connected,
            "xml_responding": diagnostics.xml_responding,
            "configured_host": diagnostics.configured_host,
            "resolved_ip": diagnostics.resolved_ip,
            "port": diagnostics.port,
            "tally_version": diagnostics.tally_version,
            "company_name": diagnostics.company_name,
            "message": diagnostics.user_message,
            "status": diagnostics.status.value,
            "stages": [
                {
                    "stage": stage.stage.value,
                    "label": _stage_label(stage.stage.value),
                    "success": stage.success,
                    "message": stage.message,
                }
                for stage in diagnostics.stages
            ],
        }


def _stage_label(stage: str) -> str:
    return {
        "host_resolution": "Host Resolution",
        "tcp_connection": "TCP Connection",
        "xml_server": "XML Server",
    }.get(stage, stage.replace("_", " ").title())


def _status_message(status: str, enabled: bool) -> str:
    if not enabled:
        return "Tally integration is disabled."
    if status == TallyConnectivityStatus.CONNECTED.value:
        return "Tally workstation is connected."
    if status == TallyConnectivityStatus.XML_ERROR.value:
        return "Please ensure Tally Prime is running and XML Server is enabled."
    return "Waiting for the Tally workstation to become available."
