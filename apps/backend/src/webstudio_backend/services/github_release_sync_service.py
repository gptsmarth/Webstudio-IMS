"""GitHub Releases synchronization — poll, compare, download, verify (M13B)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus
from webstudio_backend.infrastructure.database.models.release_download_job import (
    ReleaseDownloadArtifact,
    ReleaseDownloadJob,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.release_download_repository import (
    ReleaseDownloadRepository,
)
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.github_release_client import GitHubRelease, GitHubReleaseClient
from webstudio_backend.services.release_catalog_loader import release_from_bundle_dir
from webstudio_backend.services.release_download_service import ReleaseDownloadService
from webstudio_backend.services.release_manifest_validator import (
    parse_checksums_file,
    validate_release_manifest,
)
from webstudio_backend.services.release_semver import (
    compare_semver,
    is_valid_semver,
    normalize_tag,
    parse_build_number_from_version,
)
from webstudio_backend.services.release_storage_paths import resolve_release_updates_root
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService

RELEASE_SYNC_SCHEDULER_KEY = "github_release_sync"
MANIFEST_ASSET_NAMES = {"version-manifest.json"}
CHECKSUM_ASSET_NAMES = {"checksums.sha256"}
NOTES_ASSET_NAMES = {"RELEASE_NOTES.md"}


async def ensure_github_release_sync_enabled(
    session: AsyncSession,
    settings: Settings,
) -> bool:
    """Turn on GitHub release sync when production env is configured."""
    if settings.is_test or not settings.webstudio_release_sync_scheduler:
        return False
    repo = settings.github_repo.strip() or (
        await SystemSettingRepository(session).get_string("github_release_repo") or ""
    ).strip()
    if not repo:
        return False
    settings_repo = SystemSettingRepository(session)
    if await settings_repo.get_bool("github_release_sync_enabled", default=False):
        return True
    from webstudio_backend.infrastructure.database.enums import SettingValueType

    await settings_repo.set_value(
        "github_release_sync_enabled",
        True,
        value_type=SettingValueType.BOOLEAN,
    )
    logger.info("github.release_sync.auto_enabled", repo=repo)
    return True


class GitHubReleaseSyncService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._download_repo = ReleaseDownloadRepository(session)
        self._release_repo = SoftwareReleaseRepository(session)
        self._settings_repo = SystemSettingRepository(session)
        self._enterprise = EnterpriseReleaseService(session, settings)

    async def is_enabled(self) -> bool:
        if self._settings.is_test:
            return False
        enabled = await self._settings_repo.get_bool("github_release_sync_enabled", default=False)
        repo = await self.resolve_github_repo()
        return enabled and bool(repo)

    async def resolve_github_repo(self) -> str:
        configured = self._settings.github_repo.strip()
        if configured:
            return configured
        return (await self._settings_repo.get_string("github_release_repo") or "").strip()

    async def run_sync_cycle(self, *, force: bool = False) -> dict[str, Any]:
        if not force and not await self.is_enabled():
            return {"status": "disabled"}

        repo = await self.resolve_github_repo()
        client = GitHubReleaseClient(token=self._settings.github_token)
        channel = self._enterprise.resolve_channel()

        await self._download_repo.mark_stale_downloading_failed()
        discovered = 0
        queued = 0
        completed = 0
        failed = 0

        try:
            releases = await client.list_releases(repo)
        except Exception as exc:
            logger.warning("github.release.list_failed", error=str(exc))
            return {"status": "failed", "detail": str(exc)}

        for release in releases:
            if release.draft:
                continue
            if not is_valid_semver(normalize_tag(release.tag_name)):
                continue
            if await self._should_skip_release(release, channel):
                continue
            job = await self._enqueue_release(release, channel)
            if job is not None:
                discovered += 1
                if job.status in {ReleaseDownloadStatus.PENDING, ReleaseDownloadStatus.QUEUED}:
                    queued += 1

        retryable = await self._download_repo.list_retryable_jobs(limit=3)
        downloader = ReleaseDownloadService(github_token=self._settings.github_token)
        for job in retryable:
            result = await self._process_job(job, downloader)
            if result == "completed":
                completed += 1
            elif result == "failed":
                failed += 1

        runtime = SchedulerRuntimeService(self._session)
        await runtime.record_run(
            RELEASE_SYNC_SCHEDULER_KEY,
            status="ok",
            interval_seconds=self._settings.release_sync_interval_seconds,
            state_patch={
                "last_sync_at": datetime.now(UTC).isoformat(),
                "discovered": discovered,
                "queued": queued,
                "completed": completed,
                "failed": failed,
                "repo": repo,
            },
        )
        return {
            "status": "ok",
            "discovered": discovered,
            "queued": queued,
            "completed": completed,
            "failed": failed,
        }

    async def get_sync_status(self) -> dict[str, Any]:
        runtime = SchedulerRuntimeService(self._session)
        row = await runtime.get_state(RELEASE_SYNC_SCHEDULER_KEY)
        counts = await self._download_repo.count_by_status()
        latest = await self._download_repo.latest_completed_job()
        return {
            "enabled": await self.is_enabled(),
            "github_repo": await self.resolve_github_repo(),
            "polling_interval_seconds": self._settings.release_sync_interval_seconds,
            "updates_root": str(resolve_release_updates_root(self._settings)),
            "last_sync_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "last_sync_status": row.last_run_status,
            "state": row.state_json or {},
            "queue_counts": counts,
            "latest_completed": self._serialize_job_summary(latest) if latest else None,
            "auto_deploy": False,
        }

    async def get_download_history(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        page_params = PageParams(page=page, page_size=page_size)
        rows, total = await self._download_repo.list_history(
            page=page_params,
            statuses=[ReleaseDownloadStatus.COMPLETED],
        )
        return self._paginate_jobs(rows, total, page, page_size)

    async def get_failed_history(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        page_params = PageParams(page=page, page_size=page_size)
        rows, total = await self._download_repo.list_history(
            page=page_params,
            statuses=[ReleaseDownloadStatus.FAILED, ReleaseDownloadStatus.SKIPPED],
        )
        return self._paginate_jobs(rows, total, page, page_size)

    async def _should_skip_release(self, release: GitHubRelease, channel: ReleaseChannel) -> bool:
        existing_job = await self._download_repo.find_job_by_github_release(
            github_release_id=release.id,
            channel=channel,
        )
        if existing_job and existing_job.status == ReleaseDownloadStatus.COMPLETED:
            return True

        version = normalize_tag(release.tag_name)
        latest = await self._release_repo.get_latest(channel)
        if latest is None:
            return False
        try:
            return compare_semver(version, latest.release_version) <= 0
        except ValueError:
            return False

    async def _enqueue_release(
        self,
        release: GitHubRelease,
        channel: ReleaseChannel,
    ) -> ReleaseDownloadJob | None:
        existing = await self._download_repo.find_job_by_github_release(
            github_release_id=release.id,
            channel=channel,
        )
        if existing is not None:
            if existing.status == ReleaseDownloadStatus.COMPLETED:
                return existing
            return existing

        version = normalize_tag(release.tag_name)
        build_number = parse_build_number_from_version(version)
        bundle_dir = resolve_release_updates_root(self._settings) / f"v{version}"
        job = ReleaseDownloadJob(
            github_release_id=release.id,
            tag_name=release.tag_name,
            release_version=version,
            build_number=build_number,
            release_channel=channel,
            status=ReleaseDownloadStatus.QUEUED,
            bundle_dir=str(bundle_dir),
            github_payload=release.raw,
        )
        for asset in release.assets:
            if not asset.name:
                continue
            job.artifacts.append(
                ReleaseDownloadArtifact(
                    artifact_name=asset.name,
                    github_asset_id=asset.id,
                    download_url=asset.download_url,
                    file_size_bytes=asset.size,
                    status=ReleaseDownloadStatus.PENDING,
                ),
            )
        return await self._download_repo.create_job(job)

    async def _process_job(
        self,
        job: ReleaseDownloadJob,
        downloader: ReleaseDownloadService,
    ) -> str:
        job.attempt_count += 1
        job.started_at = datetime.now(UTC)
        job.status = ReleaseDownloadStatus.DOWNLOADING
        job.error_message = None
        await self._download_repo.save_job(job)

        bundle_dir = Path(job.bundle_dir or "")
        bundle_dir.mkdir(parents=True, exist_ok=True)

        try:
            for artifact in job.artifacts:
                await self._download_artifact(artifact, bundle_dir, downloader)

            manifest = await self._load_manifest(bundle_dir, job)
            validation = validate_release_manifest(manifest)
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
            job.manifest_validated = True

            checksums = await self._load_checksums(bundle_dir, job)
            verified = await self._verify_checksums(bundle_dir, checksums, job)
            job.checksums_verified = verified

            release = release_from_bundle_dir(
                bundle_dir, channel=job.release_channel, mark_current=False
            )
            if release is not None:
                await self._release_repo.upsert_release(release)

            job.status = ReleaseDownloadStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.next_retry_at = None
            await self._download_repo.save_job(job)
            await self._publish_client_update_catalog(job)
            return "completed"
        except Exception as exc:
            job.status = ReleaseDownloadStatus.FAILED
            job.error_message = str(exc)
            job.next_retry_at = datetime.now(UTC) + timedelta(
                minutes=min(60, job.attempt_count * 5)
            )
            await self._download_repo.save_job(job)
            logger.warning(
                "github.release.download_failed",
                tag=job.tag_name,
                error=str(exc),
            )
            return "failed"

    async def _publish_client_update_catalog(self, job: ReleaseDownloadJob) -> None:
        """Expose a verified download to desktop/mobile clients without a full server deploy."""
        release = await self._release_repo.find_existing(
            release_version=job.release_version,
            build_number=job.build_number,
            channel=job.release_channel,
        )
        if release is None:
            return

        current = await self._release_repo.get_current(job.release_channel)
        if current is not None and current.id != release.id:
            try:
                if compare_semver(release.release_version, current.release_version) < 0:
                    return
            except ValueError:
                pass

        await self._release_repo.clear_current_flags(job.release_channel)
        release.is_current = True
        if release.published_at is None:
            release.published_at = datetime.now(UTC)
        release = await self._release_repo.upsert_release(release)

        from webstudio_backend.services.client_update_service import ClientUpdateService

        payload = EnterpriseReleaseService._serialize_release(release)  # noqa: SLF001
        await ClientUpdateService(self._session, self._settings).sync_platform_settings_from_release(
            payload,
        )
        logger.info(
            "github.release.client_catalog_published",
            version=release.release_version,
            build=release.build_number,
        )

    async def _download_artifact(
        self,
        artifact: ReleaseDownloadArtifact,
        bundle_dir: Path,
        downloader: ReleaseDownloadService,
    ) -> None:
        if not artifact.download_url:
            artifact.status = ReleaseDownloadStatus.SKIPPED
            await self._download_repo.save_artifact(artifact)
            return

        destination = bundle_dir / artifact.artifact_name
        partial = destination.with_suffix(destination.suffix + ".part")
        existing_bytes = artifact.bytes_downloaded
        if partial.is_file():
            existing_bytes = max(existing_bytes, downloader.file_size(partial))
        elif destination.is_file():
            existing_bytes = downloader.file_size(destination)
            artifact.bytes_downloaded = existing_bytes
            artifact.local_path = str(destination)
            artifact.status = ReleaseDownloadStatus.COMPLETED
            await self._download_repo.save_artifact(artifact)
            return

        artifact.status = ReleaseDownloadStatus.DOWNLOADING
        artifact.attempt_count += 1
        artifact.partial_path = str(partial)
        await self._download_repo.save_artifact(artifact)

        from webstudio_backend.services.github_release_client import GitHubReleaseAsset

        asset = GitHubReleaseAsset(
            id=int(artifact.github_asset_id or 0),
            name=artifact.artifact_name,
            size=int(artifact.file_size_bytes or 0),
            download_url=artifact.download_url,
            content_type="application/octet-stream",
        )
        downloaded = await downloader.download_asset_resumable(
            asset,
            destination=destination,
            partial_path=partial,
            existing_bytes=existing_bytes,
        )
        artifact.bytes_downloaded = downloaded
        artifact.local_path = str(destination)
        artifact.status = ReleaseDownloadStatus.COMPLETED
        await self._download_repo.save_artifact(artifact)

    async def _load_manifest(self, bundle_dir: Path, job: ReleaseDownloadJob) -> dict[str, Any]:
        manifest_path = bundle_dir / "version-manifest.json"
        if not manifest_path.is_file():
            for artifact in job.artifacts:
                if artifact.artifact_name in MANIFEST_ASSET_NAMES and artifact.local_path:
                    manifest_path = Path(artifact.local_path)
                    break
        if not manifest_path.is_file():
            raise ValueError("version-manifest.json not found in release bundle")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    async def _load_checksums(self, bundle_dir: Path, job: ReleaseDownloadJob) -> dict[str, str]:
        checksums_path = bundle_dir / "checksums.sha256"
        if not checksums_path.is_file():
            for artifact in job.artifacts:
                if artifact.artifact_name in CHECKSUM_ASSET_NAMES and artifact.local_path:
                    checksums_path = Path(artifact.local_path)
                    break
        if not checksums_path.is_file():
            return {}
        return parse_checksums_file(checksums_path.read_text(encoding="utf-8"))

    async def _verify_checksums(
        self,
        bundle_dir: Path,
        checksums: dict[str, str],
        job: ReleaseDownloadJob,
    ) -> bool:
        if not checksums:
            return False
        downloader = ReleaseDownloadService()
        verified_all = True
        for artifact in job.artifacts:
            if (
                artifact.artifact_name
                in MANIFEST_ASSET_NAMES | CHECKSUM_ASSET_NAMES | NOTES_ASSET_NAMES
            ):
                expected = checksums.get(artifact.artifact_name)
                if not expected or not artifact.local_path:
                    continue
                if not downloader.verify_sha256(Path(artifact.local_path), expected):
                    verified_all = False
                    artifact.status = ReleaseDownloadStatus.FAILED
                    artifact.error_message = "SHA256 mismatch"
                    await self._download_repo.save_artifact(artifact)
        return verified_all

    @staticmethod
    def _serialize_job_summary(job: ReleaseDownloadJob | None) -> dict[str, Any] | None:
        if job is None:
            return None
        return {
            "id": job.id,
            "tag_name": job.tag_name,
            "release_version": job.release_version,
            "build_number": job.build_number,
            "release_channel": job.release_channel.value,
            "status": job.status.value,
            "bundle_dir": job.bundle_dir,
            "manifest_validated": job.manifest_validated,
            "checksums_verified": job.checksums_verified,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
        }

    @staticmethod
    def _paginate_jobs(
        rows: list[ReleaseDownloadJob],
        total: int,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
        return {
            "items": [
                {
                    "id": row.id,
                    "tag_name": row.tag_name,
                    "release_version": row.release_version,
                    "build_number": row.build_number,
                    "release_channel": row.release_channel.value,
                    "status": row.status.value,
                    "bundle_dir": row.bundle_dir,
                    "manifest_validated": row.manifest_validated,
                    "checksums_verified": row.checksums_verified,
                    "attempt_count": row.attempt_count,
                    "error_message": row.error_message,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "artifact_count": len(row.artifacts),
                }
                for row in rows
            ],
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
