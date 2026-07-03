"""mDNS / Bonjour advertisement for WEBSTUDIO IMS backend servers."""

from __future__ import annotations

import logging
import socket
import threading
from typing import TYPE_CHECKING

from webstudio_backend.core.network.discovery_constants import (
    DISCOVERY_PROTOCOL_VERSION,
    DISCOVERY_SERVICE_TYPE,
    DiscoveryTxtKey,
)
from webstudio_backend.services.platform_info_service import resolve_build_version

if TYPE_CHECKING:
    from webstudio_backend.core.config import Settings

logger = logging.getLogger(__name__)


def _pick_lan_ip() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        probe.close()
        return address
    except OSError:
        return "127.0.0.1"


def _sanitize_txt_value(value: str, *, max_length: int = 255) -> str:
    cleaned = value.replace("\x00", "").strip()
    return cleaned[:max_length]


class MdnsAdvertisementService:
    """Registers the backend on the LAN via Zeroconf / mDNS."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._zeroconf = None
        self._service_info = None
        self._lock = threading.Lock()
        self._started = False
        self._start_thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        if self._settings.is_test:
            return False
        return self._settings.mdns_enabled

    def start(self, *, company_name: str = "", server_name: str | None = None) -> None:
        if not self.enabled:
            logger.debug("mDNS advertisement disabled for this environment.")
            return
        with self._lock:
            if self._started or self._start_thread is not None:
                return
            self._start_thread = threading.Thread(
                target=self._start_blocking,
                kwargs={"company_name": company_name, "server_name": server_name},
                name="webstudio-mdns-start",
                daemon=True,
            )
            self._start_thread.start()

    def _start_blocking(self, *, company_name: str, server_name: str | None) -> None:
        """Run Zeroconf registration off the ASGI event loop (zeroconf blocks asyncio)."""
        try:
            from zeroconf import IPVersion, ServiceInfo, Zeroconf
        except ImportError:
            logger.warning("zeroconf package not installed — LAN discovery advertisement skipped.")
            return

        try:
            resolved_name = (
                server_name or self._settings.mdns_server_name or socket.gethostname()
            ).strip()
            if not resolved_name:
                resolved_name = "WEBSTUDIO-SERVER"
            service_name = f"{resolved_name}.{DISCOVERY_SERVICE_TYPE}"
            lan_ip = _pick_lan_ip()
            port = self._settings.api_port
            properties = {
                key.encode(): _sanitize_txt_value(value).encode()
                for key, value in {
                    DiscoveryTxtKey.SERVER_NAME.value: resolved_name,
                    DiscoveryTxtKey.COMPANY_NAME.value: company_name or "WEBSTUDIO",
                    DiscoveryTxtKey.BACKEND_VERSION.value: self._settings.app_version,
                    DiscoveryTxtKey.API_VERSION.value: self._settings.api_version,
                    DiscoveryTxtKey.BACKEND_PORT.value: str(port),
                    DiscoveryTxtKey.ENVIRONMENT.value: self._settings.app_env,
                    DiscoveryTxtKey.BUILD_VERSION.value: resolve_build_version(self._settings),
                    DiscoveryTxtKey.PROTOCOL_VERSION.value: DISCOVERY_PROTOCOL_VERSION,
                }.items()
            }
            zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            service_info = ServiceInfo(
                DISCOVERY_SERVICE_TYPE,
                service_name,
                addresses=[socket.inet_aton(lan_ip)],
                port=port,
                properties=properties,
                server=f"{resolved_name}.local.",
            )
            zeroconf.register_service(service_info)
            with self._lock:
                self._zeroconf = zeroconf
                self._service_info = service_info
                self._started = True
            logger.info(
                "mDNS advertisement started for %s on %s:%s",
                service_name,
                lan_ip,
                port,
            )
        except (OSError, PermissionError) as exc:
            logger.warning("mDNS advertisement skipped — network unavailable: %s", exc)
        except Exception:
            logger.exception("Failed to start mDNS advertisement.")
        finally:
            with self._lock:
                self._start_thread = None

    def update_company_name(self, company_name: str) -> None:
        if not self._started or self._service_info is None or self._zeroconf is None:
            return
        with self._lock:
            properties = dict(self._service_info.properties or {})
            properties[DiscoveryTxtKey.COMPANY_NAME.value.encode()] = _sanitize_txt_value(
                company_name or "WEBSTUDIO",
            ).encode("utf-8")
            self._service_info.properties = properties
            try:
                self._zeroconf.update_service(self._service_info)
            except Exception:
                logger.exception("Failed to update mDNS TXT record for company name.")

    def stop(self) -> None:
        with self._lock:
            start_thread = self._start_thread
            if not self._started and start_thread is None:
                return
        if start_thread is not None and start_thread.is_alive():
            start_thread.join(timeout=5.0)
        with self._lock:
            if not self._started:
                return
            try:
                if self._zeroconf is not None and self._service_info is not None:
                    self._zeroconf.unregister_service(self._service_info)
                    self._zeroconf.close()
            except Exception:
                logger.exception("Error stopping mDNS advertisement.")
            finally:
                self._zeroconf = None
                self._service_info = None
                self._started = False
                self._start_thread = None
                logger.info("mDNS advertisement stopped.")
