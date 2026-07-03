"""Enterprise release management — server-side metadata authority (M13)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.services.enterprise_version_service import EnterpriseVersionService
from webstudio_backend.services.platform_info_service import (
    resolve_build_version,
    resolve_schema_version,
)
from webstudio_backend.services.release_catalog_loader import (
    build_compatibility_matrix,
    build_supported_platforms,
    default_release_channel_for_env,
    discover_bundle_dirs,
    release_from_bundle_dir,
)


class EnterpriseReleaseService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = SoftwareReleaseRepository(session)

    def resolve_channel(self, channel: ReleaseChannel | None = None) -> ReleaseChannel:
        if channel is not None:
            return channel
        configured = (self._settings.release_channel or "").strip().lower()
        if configured in {item.value for item in ReleaseChannel}:
            return ReleaseChannel(configured)
        return default_release_channel_for_env(self._settings.app_env)

    async def ensure_catalog_bootstrapped(self) -> None:
        if await self._repo.count_all() > 0:
            return
        catalog_root = self._resolve_catalog_root()
        if catalog_root is None:
            await self._seed_running_release()
            return

        bundles = discover_bundle_dirs(catalog_root)
        if not bundles:
            await self._seed_running_release()
            return

        for index, bundle_dir in enumerate(bundles):
            release = release_from_bundle_dir(
                bundle_dir,
                channel=self.resolve_channel(),
                mark_current=index == len(bundles) - 1,
            )
            if release is None:
                continue
            if release.is_current:
                await self._repo.clear_current_flags(release.release_channel)
            await self._repo.upsert_release(release)
        await self._session.commit()

    async def get_current_release(self) -> dict[str, Any]:
        await self.ensure_catalog_bootstrapped()
        channel = self.resolve_channel()
        row = await self._repo.get_current(channel)
        if row is None:
            row = await self._repo.get_latest(channel)
        if row is not None:
            payload = self._serialize_release(row)
            payload["installed_on_server"] = row.release_version == self._settings.app_version
            return await EnterpriseVersionService(
                self._session, self._settings
            ).enrich_release_payload(payload)
        return await EnterpriseVersionService(self._session, self._settings).enrich_release_payload(
            self._synthetic_current_payload(channel),
        )

    async def get_latest_release(self, channel: ReleaseChannel | None = None) -> dict[str, Any]:
        await self.ensure_catalog_bootstrapped()
        resolved_channel = self.resolve_channel(channel)
        row = await self._repo.get_latest(resolved_channel)
        if row is None:
            return await EnterpriseVersionService(
                self._session, self._settings
            ).enrich_release_payload(
                self._synthetic_current_payload(resolved_channel),
            )
        return await EnterpriseVersionService(self._session, self._settings).enrich_release_payload(
            self._serialize_release(row),
        )

    async def get_release_history(
        self,
        *,
        channel: ReleaseChannel | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        await self.ensure_catalog_bootstrapped()
        resolved_channel = self.resolve_channel(channel)
        page_params = PageParams(page=page, page_size=page_size)
        rows, total = await self._repo.list_history(resolved_channel, page=page_params)
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
        return {
            "channel": resolved_channel.value,
            "items": [self._serialize_release_summary(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }

    async def _seed_running_release(self) -> SoftwareRelease:
        channel = self.resolve_channel()
        await self._repo.clear_current_flags(channel)
        schema_version = await resolve_schema_version(self._session)
        manifest = {
            "schema_version": "2.0.0",
            "product": "WEBSTUDIO IMS",
            "release_version": self._settings.app_version,
            "build": {
                "timestamp": datetime.now(UTC).isoformat(),
                "git_commit": resolve_build_version(self._settings),
                "git_short": resolve_build_version(self._settings)[:7],
            },
            "components": {
                "backend": {
                    "app_version": self._settings.app_version,
                    "api_version": self._settings.api_version,
                    "min_client_version": self._settings.min_client_version,
                    "min_desktop_version": self._settings.min_desktop_version,
                    "min_mobile_version": self._settings.min_mobile_version,
                },
            },
            "database": {"alembic_head": schema_version},
            "release": {
                "channel": channel.value,
                "build_number": self._settings.build_number,
            },
        }
        release = SoftwareRelease(
            release_version=self._settings.app_version,
            build_number=self._settings.build_number,
            release_channel=channel,
            git_commit=resolve_build_version(self._settings),
            git_short=resolve_build_version(self._settings)[:7],
            build_timestamp=datetime.now(UTC),
            release_notes=None,
            manifest=manifest,
            checksums={},
            compatibility_matrix=build_compatibility_matrix(manifest),
            supported_platforms=build_supported_platforms(manifest),
            is_current=True,
            published_at=datetime.now(UTC),
        )
        saved = await self._repo.upsert_release(release)
        await self._session.commit()
        return saved

    def _resolve_catalog_root(self) -> Path | None:
        configured = self._settings.release_catalog_root.strip()
        if configured:
            path = Path(configured)
            return path if path.is_dir() else None
        repo_guess = Path(__file__).resolve().parents[5] / "release"
        return repo_guess if repo_guess.is_dir() else None

    def _synthetic_current_payload(self, channel: ReleaseChannel) -> dict[str, Any]:
        manifest = {
            "schema_version": "2.0.0",
            "release_version": self._settings.app_version,
            "components": {
                "backend": {
                    "app_version": self._settings.app_version,
                    "api_version": self._settings.api_version,
                    "min_client_version": self._settings.min_client_version,
                    "min_desktop_version": self._settings.min_desktop_version,
                    "min_mobile_version": self._settings.min_mobile_version,
                },
            },
            "release": {"channel": channel.value, "build_number": self._settings.build_number},
        }
        return {
            "release_version": self._settings.app_version,
            "build_number": self._settings.build_number,
            "release_channel": channel.value,
            "git_commit": resolve_build_version(self._settings),
            "git_short": resolve_build_version(self._settings)[:7],
            "build_timestamp": datetime.now(UTC).isoformat(),
            "release_notes": None,
            "manifest": manifest,
            "checksums": {},
            "compatibility_matrix": build_compatibility_matrix(manifest),
            "supported_platforms": build_supported_platforms(manifest),
            "is_current": True,
            "published_at": datetime.now(UTC).isoformat(),
            "installed_on_server": True,
            "source": "runtime",
        }

    @staticmethod
    def _serialize_release(row: SoftwareRelease) -> dict[str, Any]:
        return {
            "id": row.id,
            "release_version": row.release_version,
            "build_number": row.build_number,
            "release_channel": row.release_channel.value,
            "git_commit": row.git_commit,
            "git_short": row.git_short,
            "build_timestamp": row.build_timestamp.isoformat(),
            "release_notes": row.release_notes,
            "manifest": row.manifest or {},
            "checksums": row.checksums or {},
            "compatibility_matrix": row.compatibility_matrix or {},
            "supported_platforms": row.supported_platforms or [],
            "is_current": row.is_current,
            "published_at": row.published_at.isoformat(),
            "source": "catalog",
        }

    @staticmethod
    def _serialize_release_summary(row: SoftwareRelease) -> dict[str, Any]:
        return {
            "id": row.id,
            "release_version": row.release_version,
            "build_number": row.build_number,
            "release_channel": row.release_channel.value,
            "git_short": row.git_short,
            "build_timestamp": row.build_timestamp.isoformat(),
            "is_current": row.is_current,
            "published_at": row.published_at.isoformat(),
        }
