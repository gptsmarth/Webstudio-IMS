"""Enterprise centralized version identity — VERSION.json + runtime database revision."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.core.version_catalog import (
    VersionCatalog,
    load_version_catalog,
    resolve_git_commit,
    resolve_git_short,
)
from webstudio_backend.services.platform_info_service import resolve_schema_version


class EnterpriseVersionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._catalog = load_version_catalog()

    async def build_version_identity(self) -> dict[str, Any]:
        database_revision = await resolve_schema_version(self._session)
        git_commit = resolve_git_commit(catalog=self._catalog, fallback=self._settings.build_version)
        git_short = resolve_git_short(git_commit, catalog=self._catalog)
        release_channel = self._resolve_release_channel()
        release_date = self._resolve_release_date()

        return {
            "version": self._resolve_version(),
            "build_number": self._resolve_build_number(),
            "git_commit": git_commit,
            "git_short": git_short,
            "release_date": release_date,
            "release_channel": release_channel,
            "database_revision": database_revision,
            "product": self._catalog.product,
            "source": str(self._catalog.source_path) if self._catalog.source_path else "defaults",
        }

    def catalog_snapshot(self) -> VersionCatalog:
        return self._catalog

    def _resolve_version(self) -> str:
        if self._settings.app_version.strip():
            return self._settings.app_version.strip()
        return self._catalog.version

    def _resolve_build_number(self) -> int:
        if self._settings.build_number > 0:
            return self._settings.build_number
        return self._catalog.build_number

    def _resolve_release_channel(self) -> str:
        if self._settings.release_channel.strip():
            return self._settings.release_channel.strip().lower()
        return self._catalog.release_channel.strip().lower() or "development"

    def _resolve_release_date(self) -> str | None:
        if self._catalog.release_date.strip():
            return self._catalog.release_date.strip()
        return None

    async def enrich_release_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        identity = await self.build_version_identity()
        manifest = payload.get("manifest") or {}
        database = manifest.get("database") or {}
        database_revision = (
            str(database.get("alembic_head") or "").strip()
            or identity["database_revision"]
        )

        enriched = dict(payload)
        enriched["release_date"] = payload.get("published_at") or identity["release_date"]
        enriched["database_revision"] = database_revision
        enriched["version_identity"] = {
            **identity,
            "database_revision": database_revision,
            "release_date": enriched["release_date"],
        }
        return enriched
