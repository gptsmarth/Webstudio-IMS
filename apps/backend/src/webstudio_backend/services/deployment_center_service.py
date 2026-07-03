"""Deployment Center — administrator-controlled release lifecycle (M13C)."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus
from webstudio_backend.infrastructure.database.models.release_deployment_event import ReleaseDeploymentEvent
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.release_deployment_repository import (
    ReleaseDeploymentRepository,
)
from webstudio_backend.infrastructure.repositories.release_download_repository import ReleaseDownloadRepository
from webstudio_backend.infrastructure.repositories.software_release_repository import SoftwareReleaseRepository
from webstudio_backend.services.enterprise_release_service import EnterpriseReleaseService
from webstudio_backend.services.github_release_client import GitHubReleaseClient
from webstudio_backend.services.github_release_sync_service import GitHubReleaseSyncService
from webstudio_backend.services.release_download_service import ReleaseDownloadService
from webstudio_backend.services.release_manifest_validator import validate_release_manifest
from webstudio_backend.services.release_semver import compare_semver, is_valid_semver, normalize_tag
from webstudio_backend.services.enterprise_deployment_engine import EnterpriseDeploymentEngine
from webstudio_backend.services.enterprise_rollback_engine import EnterpriseRollbackEngine
from webstudio_backend.services.release_storage_paths import resolve_release_updates_root


class DeploymentCenterService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._enterprise = EnterpriseReleaseService(session, settings)
        self._sync = GitHubReleaseSyncService(session, settings)
        self._download_repo = ReleaseDownloadRepository(session)
        self._release_repo = SoftwareReleaseRepository(session)
        self._deployment_repo = ReleaseDeploymentRepository(session)

    async def get_dashboard(self) -> dict[str, Any]:
        channel = self._enterprise.resolve_channel()
        current = await self._enterprise.get_current_release()
        latest = await self._enterprise.get_latest_release(channel)
        downloaded_job = await self._download_repo.latest_completed_job()
        sync_status = await self._sync.get_sync_status()
        packages, _ = await self._download_repo.list_history(
            page=PageParams(page=1, page_size=20),
            statuses=[ReleaseDownloadStatus.COMPLETED],
        )

        compatibility = self._compatibility_status(current, latest)
        deployment_status = self._resolve_deployment_status(current, latest, downloaded_job)

        return {
            "current_version": current.get("release_version"),
            "latest_version": latest.get("release_version"),
            "downloaded_version": downloaded_job.release_version if downloaded_job else None,
            "release_channel": channel.value,
            "build_number": current.get("build_number"),
            "git_commit": current.get("git_commit"),
            "git_short": current.get("git_short"),
            "release_date": latest.get("published_at") or current.get("published_at"),
            "compatibility_status": compatibility,
            "downloaded_packages": [self._serialize_package(row) for row in packages],
            "deployment_status": deployment_status,
            "updates_root": str(resolve_release_updates_root(self._settings)),
            "sync_enabled": sync_status.get("enabled", False),
            "github_repo": sync_status.get("github_repo", ""),
            "auto_deploy": False,
        }

    async def check_updates(self, *, user_id: int | None) -> dict[str, Any]:
        event = await self._start_event("check_updates", user_id=user_id)
        try:
            repo = await self._sync.resolve_github_repo()
            if not repo:
                raise ValueError("GitHub repository is not configured")
            client = GitHubReleaseClient(token=self._settings.github_token)
            releases = await client.list_releases(repo)
            channel = self._enterprise.resolve_channel()
            current = await self._enterprise.get_current_release()
            available = []
            for release in releases:
                if release.draft or not is_valid_semver(normalize_tag(release.tag_name)):
                    continue
                version = normalize_tag(release.tag_name)
                try:
                    if compare_semver(version, current["release_version"]) > 0:
                        available.append(
                            {
                                "tag_name": release.tag_name,
                                "release_version": version,
                                "published_at": release.published_at,
                                "prerelease": release.prerelease,
                            },
                        )
                except ValueError:
                    continue
            await self._deployment_repo.complete_event(
                event,
                status="completed",
                detail_patch={"updates_found": len(available), "releases": available},
            )
            return {"updates_found": len(available), "releases": available}
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def download_updates(self, *, user_id: int | None, job_id: int | None = None) -> dict[str, Any]:
        event = await self._start_event("download", user_id=user_id)
        try:
            await self._sync.run_sync_cycle(force=True)
            jobs = await self._download_repo.list_retryable_jobs(limit=5)
            if job_id is not None:
                jobs = [job for job in jobs if job.id == job_id]
            if not jobs and job_id is not None:
                job = await self._download_repo.get_job_by_id(job_id)
                if job is not None:
                    jobs = [job]
            if not jobs:
                result = await self._sync.run_sync_cycle()
                await self._deployment_repo.complete_event(event, status="completed", detail_patch=result)
                return result
            downloader = ReleaseDownloadService(github_token=self._settings.github_token)
            outcomes = []
            for job in jobs[:1]:
                outcome = await self._sync._process_job(job, downloader)  # noqa: SLF001
                outcomes.append({"job_id": job.id, "outcome": outcome})
            await self._deployment_repo.complete_event(
                event,
                status="completed",
                detail_patch={"outcomes": outcomes},
            )
            return {"outcomes": outcomes}
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def validate_package(self, *, user_id: int | None, job_id: int) -> dict[str, Any]:
        job = await self._download_repo.get_job_by_id(job_id)
        if job is None:
            raise ValueError("Download job not found")
        event = await self._start_event(
            "validate",
            user_id=user_id,
            release_version=job.release_version,
            build_number=job.build_number,
            channel=job.release_channel,
            job_id=job.id,
        )
        try:
            bundle_dir = Path(job.bundle_dir or "")
            manifest_path = bundle_dir / "version-manifest.json"
            if not manifest_path.is_file():
                raise ValueError("version-manifest.json missing")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validation = validate_release_manifest(manifest)
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
            job.manifest_validated = True
            checksums_path = bundle_dir / "checksums.sha256"
            if checksums_path.is_file():
                from webstudio_backend.services.release_manifest_validator import parse_checksums_file

                checksums = parse_checksums_file(checksums_path.read_text(encoding="utf-8"))
                downloader = ReleaseDownloadService()
                verified = True
                for artifact in job.artifacts:
                    if artifact.local_path and artifact.artifact_name in checksums:
                        if not downloader.verify_sha256(Path(artifact.local_path), checksums[artifact.artifact_name]):
                            verified = False
                job.checksums_verified = verified
            await self._download_repo.save_job(job)
            await self._deployment_repo.complete_event(
                event,
                status="completed",
                detail_patch={
                    "manifest_validated": job.manifest_validated,
                    "checksums_verified": job.checksums_verified,
                },
            )
            return {
                "job_id": job.id,
                "manifest_validated": job.manifest_validated,
                "checksums_verified": job.checksums_verified,
            }
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def deploy_release(
        self,
        *,
        user_id: int,
        job_id: int,
        administrator_approved: bool,
    ) -> dict[str, Any]:
        if not administrator_approved:
            raise ValueError("Administrator approval is required before deployment")
        job = await self._download_repo.get_job_by_id(job_id)
        if job is None:
            raise ValueError("Download job not found")
        if job.status != ReleaseDownloadStatus.COMPLETED:
            raise ValueError("Package must be downloaded and validated before deployment")
        if not job.manifest_validated:
            raise ValueError("Run validation before deployment")

        release = await self._release_repo.find_existing(
            release_version=job.release_version,
            build_number=job.build_number,
            channel=job.release_channel,
        )
        if release is None:
            raise ValueError("Release metadata not found in catalog")

        event = await self._start_event(
            "deploy",
            user_id=user_id,
            release_version=job.release_version,
            build_number=job.build_number,
            channel=job.release_channel,
            job_id=job.id,
            approved=True,
        )
        try:
            engine = EnterpriseDeploymentEngine(self._session, self._settings)
            outcome = await engine.execute_deploy(
                job_id=job.id,
                user_id=user_id,
                release_version=job.release_version,
                build_number=job.build_number,
                release_channel=job.release_channel,
                bundle_dir=job.bundle_dir or "",
            )
            await self._deployment_repo.complete_event(
                event,
                status="completed",
                detail_patch={"run_id": outcome["run_id"], "steps": len(outcome.get("steps", []))},
            )
            return {
                "release_version": outcome["release_version"],
                "build_number": outcome["build_number"],
                "run_id": outcome["run_id"],
                "deployed": True,
                "status": outcome["status"],
                "steps": outcome.get("steps", []),
            }
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def get_deployment_run(self, run_id: int) -> dict[str, Any]:
        engine = EnterpriseDeploymentEngine(self._session, self._settings)
        payload = await engine.get_run(run_id)
        if payload is None:
            raise ValueError("Deployment run not found")
        return payload

    async def get_latest_deployment_run(self) -> dict[str, Any] | None:
        engine = EnterpriseDeploymentEngine(self._session, self._settings)
        return await engine.get_latest_run()

    async def rollback_release(self, *, user_id: int, administrator_approved: bool) -> dict[str, Any]:
        if not administrator_approved:
            raise ValueError("Administrator approval is required before rollback")
        channel = self._enterprise.resolve_channel()
        rows, total = await self._release_repo.list_history(channel, page=PageParams(page=1, page_size=5))
        if len(rows) < 2:
            raise ValueError("No previous release available for rollback")
        current = next((row for row in rows if row.is_current), rows[0])
        previous = next((row for row in rows if row.id != current.id), None)
        if previous is None:
            raise ValueError("No previous release available for rollback")

        event = await self._start_event(
            "rollback",
            user_id=user_id,
            release_version=previous.release_version,
            build_number=previous.build_number,
            channel=channel,
            approved=True,
        )
        try:
            engine = EnterpriseRollbackEngine(self._session, self._settings)
            outcome = await engine.execute_rollback(
                user_id=user_id,
                deployment_event_id=event.id,
            )
            await self._deployment_repo.complete_event(
                event,
                status="completed",
                detail_patch={
                    "rollback_run_id": outcome["run_id"],
                    "from_release_id": outcome.get("from_release_id"),
                    "to_release_id": outcome.get("to_release_id"),
                },
            )
            return {
                "from_version": outcome["from_release_version"],
                "to_version": outcome["to_release_version"],
                "run_id": outcome["run_id"],
                "rolled_back": True,
                "status": outcome["status"],
                "health_status": outcome.get("health_status", {}),
                "steps": outcome.get("steps", []),
            }
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def get_rollback_history(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        engine = EnterpriseRollbackEngine(self._session, self._settings)
        return await engine.list_history(page=page, page_size=page_size)

    async def get_rollback_run(self, run_id: int) -> dict[str, Any]:
        engine = EnterpriseRollbackEngine(self._session, self._settings)
        payload = await engine.get_run(run_id)
        if payload is None:
            raise ValueError("Rollback run not found")
        return payload

    async def delete_package(
        self,
        *,
        user_id: int,
        job_id: int,
        administrator_approved: bool,
    ) -> dict[str, Any]:
        if not administrator_approved:
            raise ValueError("Administrator approval is required before deleting a package")
        job = await self._download_repo.get_job_by_id(job_id)
        if job is None:
            raise ValueError("Download job not found")
        event = await self._start_event(
            "delete_package",
            user_id=user_id,
            release_version=job.release_version,
            build_number=job.build_number,
            channel=job.release_channel,
            job_id=job.id,
            approved=True,
        )
        try:
            if job.bundle_dir:
                path = Path(job.bundle_dir)
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
            job.status = ReleaseDownloadStatus.SKIPPED
            job.error_message = "Deleted by administrator"
            await self._download_repo.save_job(job)
            await self._deployment_repo.complete_event(event, status="completed")
            return {"job_id": job.id, "deleted": True}
        except Exception as exc:
            await self._deployment_repo.complete_event(event, status="failed", error_message=str(exc))
            raise

    async def get_deployment_history(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        rows, total = await self._deployment_repo.list_events(page=PageParams(page=page, page_size=page_size))
        return self._paginate_events(rows, total, page, page_size)

    async def get_deployment_logs(self, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        rows, total = await self._deployment_repo.list_events(page=PageParams(page=page, page_size=page_size))
        return self._paginate_events(rows, total, page, page_size)

    async def get_analytics(self) -> dict[str, Any]:
        from webstudio_backend.services.deployment_monitoring_service import DeploymentMonitoringService

        return await DeploymentMonitoringService(self._session, self._settings).get_analytics()

    async def _start_event(
        self,
        event_type: str,
        *,
        user_id: int | None,
        release_version: str | None = None,
        build_number: int | None = None,
        channel: ReleaseChannel | None = None,
        job_id: int | None = None,
        approved: bool = False,
    ) -> ReleaseDeploymentEvent:
        return await self._deployment_repo.create_event(
            ReleaseDeploymentEvent(
                event_type=event_type,
                status="running",
                release_version=release_version,
                build_number=build_number,
                release_channel=channel,
                job_id=job_id,
                administrator_approved=approved,
                performed_by_user_id=user_id,
            ),
        )

    @staticmethod
    def _compatibility_status(current: dict[str, Any], latest: dict[str, Any]) -> str:
        try:
            if compare_semver(latest["release_version"], current["release_version"]) > 0:
                matrix = latest.get("compatibility_matrix") or {}
                min_client = matrix.get("min_client_version")
                if min_client and compare_semver(current["release_version"], min_client) < 0:
                    return "incompatible"
                return "update_available"
            return "compatible"
        except ValueError:
            return "unknown"

    @staticmethod
    def _resolve_deployment_status(
        current: dict[str, Any],
        latest: dict[str, Any],
        downloaded_job: ReleaseDownloadJob | None,
    ) -> str:
        if downloaded_job and downloaded_job.release_version != current.get("release_version"):
            if downloaded_job.manifest_validated:
                return "ready_to_deploy"
            return "downloaded"
        try:
            if compare_semver(latest["release_version"], current["release_version"]) > 0:
                return "update_available"
        except ValueError:
            pass
        return "current"

    @staticmethod
    def _serialize_package(job: ReleaseDownloadJob) -> dict[str, Any]:
        return {
            "job_id": job.id,
            "tag_name": job.tag_name,
            "release_version": job.release_version,
            "build_number": job.build_number,
            "status": job.status.value,
            "bundle_dir": job.bundle_dir,
            "manifest_validated": job.manifest_validated,
            "checksums_verified": job.checksums_verified,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    @staticmethod
    def _paginate_events(
        rows: list[ReleaseDeploymentEvent],
        total: int,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
        return {
            "items": [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "status": row.status,
                    "release_version": row.release_version,
                    "build_number": row.build_number,
                    "release_channel": row.release_channel.value if row.release_channel else None,
                    "job_id": row.job_id,
                    "administrator_approved": row.administrator_approved,
                    "performed_by_user_id": row.performed_by_user_id,
                    "error_message": row.error_message,
                    "detail": row.detail_json,
                    "created_at": row.created_at.isoformat(),
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
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
