"""Enterprise client update platform — server-side distribution authority (M13E)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus, SettingValueType
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.repositories.client_version_observation_repository import (
    ClientVersionObservationRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.release_catalog_loader import SUPPORTED_PLATFORMS
from webstudio_backend.services.release_semver import compare_semver, is_valid_semver

ClientPlatform = Literal[
    "desktop_windows",
    "desktop_macos",
    "mobile_android",
    "mobile_ios",
]

PLATFORM_ARTIFACT_KEYS: dict[str, str] = {
    "desktop_windows": "desktop_windows",
    "desktop_macos": "desktop_macos",
    "mobile_android": "mobile_android",
    "mobile_ios": "mobile_ios",
}

DISTRIBUTION_MODES: dict[str, str] = {
    "desktop_windows": "installer",
    "desktop_macos": "installer",
    "mobile_android": "apk_sideload",
    "mobile_ios": "app_store_notification",
}


class ClientUpdateService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._releases = EnterpriseReleaseService(session, settings)
        self._downloads = ReleaseDownloadRepository(session)
        self._settings_repo = SystemSettingRepository(session)

    async def check_for_updates(
        self,
        *,
        platform: str,
        current_version: str,
        channel: ReleaseChannel | None = None,
    ) -> dict[str, Any]:
        normalized_platform = self._normalize_platform(platform)
        resolved_channel = self._releases.resolve_channel(channel)
        latest_payload = await self._releases.get_latest_release(resolved_channel)
        latest_version = str(latest_payload.get("release_version", "0.0.0"))
        compatibility = latest_payload.get("compatibility_matrix") or {}
        platform_compat = compatibility.get(
            "desktop" if normalized_platform.startswith("desktop") else "mobile",
            {},
        )
        min_supported = str(
            platform_compat.get("min_version")
            or compatibility.get("min_client_version")
            or latest_version,
        )

        update_available = False
        mandatory = False
        if is_valid_semver(current_version) and is_valid_semver(latest_version):
            update_available = compare_semver(latest_version, current_version) > 0
            if is_valid_semver(min_supported):
                mandatory = compare_semver(current_version, min_supported) < 0

        artifact_payload: dict[str, Any] | None = None
        distribution_mode = DISTRIBUTION_MODES.get(normalized_platform, "installer")
        app_store_url: str | None = None

        if normalized_platform == "mobile_ios":
            app_store_url = await self._resolve_app_store_url(latest_payload)
            if update_available:
                distribution_mode = "app_store_notification"
        elif update_available:
            artifact = await self._resolve_artifact(
                latest_payload,
                platform=normalized_platform,
                channel=resolved_channel,
            )
            if artifact is not None:
                artifact_payload = {
                    "name": artifact["artifact_name"],
                    "sha256": artifact["sha256"],
                    "size_bytes": artifact["size_bytes"],
                    "download_url": self._build_download_url(
                        platform=normalized_platform,
                        release_version=latest_version,
                        build_number=int(latest_payload.get("build_number") or 1),
                        channel=resolved_channel.value,
                    ),
                }

        await ClientVersionObservationRepository(self._session).record_observation(
            platform=normalized_platform,
            client_version=current_version.strip(),
            release_channel=resolved_channel.value,
        )

        return {
            "platform": normalized_platform,
            "installed_version": current_version,
            "latest_version": latest_version,
            "min_supported_version": min_supported,
            "update_available": update_available,
            "mandatory": mandatory,
            "release_channel": resolved_channel.value,
            "release_notes": latest_payload.get("release_notes"),
            "published_at": latest_payload.get("published_at"),
            "distribution_mode": distribution_mode,
            "app_store_url": app_store_url,
            "artifact": artifact_payload,
            "github_contact_prohibited": True,
        }

    async def resolve_artifact_file(
        self,
        *,
        platform: str,
        release_version: str,
        build_number: int,
        channel: ReleaseChannel | None = None,
    ) -> Path:
        normalized_platform = self._normalize_platform(platform)
        resolved_channel = self._releases.resolve_channel(channel)
        release_payload = await self._find_release_payload(
            release_version=release_version,
            build_number=build_number,
            channel=resolved_channel,
        )
        artifact = await self._resolve_artifact(
            release_payload,
            platform=normalized_platform,
            channel=resolved_channel,
        )
        if artifact is None:
            raise FileNotFoundError(f"No artifact for platform {normalized_platform}")
        path = Path(artifact["local_path"])
        if not path.is_file():
            raise FileNotFoundError(f"Artifact file missing: {path}")
        return path

    async def sync_platform_settings_from_release(self, release_payload: dict[str, Any]) -> None:
        manifest = release_payload.get("manifest") or {}
        components = manifest.get("components") or {}
        release_version = str(release_payload.get("release_version", self._settings.app_version))
        channel = str(release_payload.get("release_channel", "stable"))
        build_number = int(release_payload.get("build_number") or 1)
        release_notes = release_payload.get("release_notes") or ""
        published_at = release_payload.get("published_at") or ""

        mobile_version = str((components.get("mobile_flutter") or {}).get("version", release_version))
        desktop_version = str((components.get("desktop") or {}).get("version", release_version))
        compatibility = release_payload.get("compatibility_matrix") or {}
        mobile_min = str((compatibility.get("mobile") or {}).get("min_version", release_version))
        desktop_min = str((compatibility.get("desktop") or {}).get("min_version", release_version))

        await self._settings_repo.set_value("mobile_latest_version", mobile_version, value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("mobile_release_channel", channel, value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("mobile_release_date", str(published_at), value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("mobile_release_notes", str(release_notes), value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("desktop_latest_version", desktop_version, value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("desktop_min_supported_version", desktop_min, value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("mobile_min_supported_version", mobile_min, value_type=SettingValueType.STRING)

        android_url = self._build_download_url(
            platform="mobile_android",
            release_version=release_version,
            build_number=build_number,
            channel=channel,
        )
        windows_url = self._build_download_url(
            platform="desktop_windows",
            release_version=release_version,
            build_number=build_number,
            channel=channel,
        )
        await self._settings_repo.set_value("mobile_apk_download_url", android_url, value_type=SettingValueType.STRING)
        await self._settings_repo.set_value("desktop_windows_download_url", windows_url, value_type=SettingValueType.STRING)

        ios_url = await self._resolve_app_store_url(release_payload)
        if ios_url:
            await self._settings_repo.set_value("mobile_ios_app_store_url", ios_url, value_type=SettingValueType.STRING)

    async def build_enriched_version_payload(self) -> dict[str, Any]:
        from webstudio_backend.services.platform_info_service import build_version_payload

        payload = await build_version_payload(self._session, self._settings)
        channel = self._releases.resolve_channel()
        latest = await self._releases.get_latest_release(channel)
        compatibility = latest.get("compatibility_matrix") or {}
        desktop_compat = compatibility.get("desktop") or {}
        mobile_compat = compatibility.get("mobile") or {}

        desktop_latest = (
            await self._settings_repo.get_string("desktop_latest_version")
            or str((latest.get("manifest") or {}).get("components", {}).get("desktop", {}).get("version"))
            or latest.get("release_version")
            or self._settings.app_version
        )
        desktop_min = (
            await self._settings_repo.get_string("desktop_min_supported_version")
            or desktop_compat.get("min_version")
            or self._settings.min_desktop_version
        )
        desktop_download = await self._settings_repo.get_string("desktop_windows_download_url")

        ios_store = await self._settings_repo.get_string("mobile_ios_app_store_url")

        payload["desktop"] = {
            "latest_version": desktop_latest,
            "min_supported_version": desktop_min,
            "download_url": desktop_download or None,
            "release_channel": channel.value,
        }
        mobile = dict(payload.get("mobile") or {})
        mobile["ios_app_store_url"] = ios_store or None
        mobile["ios_distribution"] = "app_store_notification"
        payload["mobile"] = mobile
        return payload

    async def _find_release_payload(
        self,
        *,
        release_version: str,
        build_number: int,
        channel: ReleaseChannel,
    ) -> dict[str, Any]:
        latest = await self._releases.get_latest_release(channel)
        if (
            latest.get("release_version") == release_version
            and int(latest.get("build_number") or 0) == build_number
        ):
            return latest
        history = await self._releases.get_release_history(channel=channel, page=1, page_size=50)
        for item in history.get("items", []):
            if item.get("release_version") == release_version and item.get("build_number") == build_number:
                return await self._releases.get_latest_release(channel)
        raise FileNotFoundError("Release not found in catalog")

    async def _resolve_artifact(
        self,
        release_payload: dict[str, Any],
        *,
        platform: str,
        channel: ReleaseChannel,
    ) -> dict[str, Any] | None:
        if platform == "mobile_ios":
            return None

        artifact_key = PLATFORM_ARTIFACT_KEYS.get(platform)
        if artifact_key is None:
            return None

        manifest = release_payload.get("manifest") or {}
        artifacts_map = manifest.get("artifacts") or {}
        artifact_name = artifacts_map.get(artifact_key)
        if not artifact_name:
            for entry in release_payload.get("supported_platforms") or []:
                if entry.get("id") == platform:
                    artifact_name = entry.get("artifact")
                    break
        if not artifact_name:
            return None

        release_version = str(release_payload.get("release_version"))
        build_number = int(release_payload.get("build_number") or 1)
        checksums = release_payload.get("checksums") or {}
        sha256 = checksums.get(artifact_name) or checksums.get(Path(artifact_name).name)

        job = await self._find_completed_job(release_version, build_number, channel)
        local_path: Path | None = None
        size_bytes: int | None = None

        if job is not None:
            for artifact in job.artifacts:
                if artifact.artifact_name == artifact_name and artifact.local_path:
                    candidate = Path(artifact.local_path)
                    if candidate.is_file():
                        local_path = candidate
                        size_bytes = artifact.file_size_bytes or candidate.stat().st_size
                        sha256 = sha256 or artifact.expected_sha256
                        break
            if local_path is None and job.bundle_dir:
                candidate = Path(job.bundle_dir) / artifact_name
                if candidate.is_file():
                    local_path = candidate
                    size_bytes = candidate.stat().st_size

        if local_path is None:
            catalog_root = self._releases._resolve_catalog_root()  # noqa: SLF001
            if catalog_root is not None:
                candidate = catalog_root / f"v{release_version}" / artifact_name
                if candidate.is_file():
                    local_path = candidate
                    size_bytes = candidate.stat().st_size

        if local_path is None:
            return None

        return {
            "artifact_name": artifact_name,
            "local_path": str(local_path),
            "sha256": sha256,
            "size_bytes": size_bytes,
        }

    async def get_artifact_checksum(
        self,
        *,
        platform: str,
        release_version: str,
        build_number: int,
        channel: ReleaseChannel | None,
        artifact_name: str,
    ) -> str | None:
        resolved_channel = self._releases.resolve_channel(channel)
        release_payload = await self._find_release_payload(
            release_version=release_version,
            build_number=build_number,
            channel=resolved_channel,
        )
        checksums = release_payload.get("checksums") or {}
        return checksums.get(artifact_name) or checksums.get(Path(artifact_name).name)

    async def _find_completed_job(
        self,
        release_version: str,
        build_number: int,
        channel: ReleaseChannel,
    ) -> ReleaseDownloadJob | None:
        result = await self._session.execute(
            select(ReleaseDownloadJob)
            .options(selectinload(ReleaseDownloadJob.artifacts))
            .where(
                ReleaseDownloadJob.release_version == release_version,
                ReleaseDownloadJob.build_number == build_number,
                ReleaseDownloadJob.release_channel == channel,
                ReleaseDownloadJob.status == ReleaseDownloadStatus.COMPLETED,
            )
            .order_by(desc(ReleaseDownloadJob.completed_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def _resolve_app_store_url(self, release_payload: dict[str, Any]) -> str | None:
        stored = await self._settings_repo.get_string("mobile_ios_app_store_url")
        if stored:
            return stored.strip() or None
        manifest = release_payload.get("manifest") or {}
        ios_meta = manifest.get("ios") or {}
        url = ios_meta.get("app_store_url")
        return str(url).strip() if url else None

    def _build_download_url(
        self,
        *,
        platform: str,
        release_version: str,
        build_number: int,
        channel: str,
    ) -> str:
        query = urlencode(
            {
                "platform": platform,
                "release_version": release_version,
                "build_number": str(build_number),
                "channel": channel,
            },
        )
        return f"/api/v1/client-updates/download?{query}"

    @staticmethod
    def _normalize_platform(platform: str) -> str:
        normalized = platform.strip().lower().replace("-", "_")
        aliases = {
            "macos_desktop": "desktop_macos",
            "windows_desktop": "desktop_windows",
            "android": "mobile_android",
            "android_mobile": "mobile_android",
            "ios": "mobile_ios",
            "ios_mobile": "mobile_ios",
            "mobile": "mobile_android",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def supported_platform_ids() -> list[str]:
        return [entry["id"] for entry in SUPPORTED_PLATFORMS] + ["mobile_ios"]
