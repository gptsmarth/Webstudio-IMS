"""Resumable release artifact downloads with SHA256 verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from webstudio_backend.services.github_release_client import GitHubReleaseAsset


class ReleaseDownloadService:
    def __init__(self, *, github_token: str = "", timeout_seconds: float = 60.0) -> None:
        self._token = github_token.strip()
        self._timeout = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "WEBSTUDIO-IMS-Release-Sync",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def download_asset_resumable(
        self,
        asset: GitHubReleaseAsset,
        *,
        destination: Path,
        partial_path: Path | None = None,
        existing_bytes: int = 0,
    ) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = partial_path or destination.with_suffix(destination.suffix + ".part")
        mode = "ab" if existing_bytes > 0 and partial.is_file() else "wb"
        if mode == "wb" and partial.exists():
            partial.unlink()

        headers = self._headers()
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"
        downloaded = existing_bytes
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(asset.download_url, headers=headers)
            response.raise_for_status()
            with partial.open(mode) as handle:
                async for chunk in response.aiter_bytes():
                    handle.write(chunk)
                    downloaded += len(chunk)

        partial.replace(destination)
        if partial.exists() and partial != destination:
            partial.unlink(missing_ok=True)
        return downloaded

    @staticmethod
    def verify_sha256(path: Path, expected_digest: str) -> bool:
        if not path.is_file():
            return False
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected_digest.strip().lower()

    @staticmethod
    def file_size(path: Path) -> int:
        return path.stat().st_size if path.is_file() else 0
