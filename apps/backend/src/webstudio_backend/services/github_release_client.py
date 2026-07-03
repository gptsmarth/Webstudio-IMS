"""GitHub Releases API client — server-side only (M13B)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class GitHubReleaseAsset:
    id: int
    name: str
    size: int
    download_url: str
    content_type: str


@dataclass(frozen=True, slots=True)
class GitHubRelease:
    id: int
    tag_name: str
    name: str
    draft: bool
    prerelease: bool
    published_at: str
    body: str
    assets: list[GitHubReleaseAsset]
    raw: dict[str, Any]


class GitHubReleaseClient:
    def __init__(self, *, token: str = "", timeout_seconds: float = 60.0) -> None:
        self._token = token.strip()
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

    async def list_releases(self, repo: str, *, per_page: int = 20) -> list[GitHubRelease]:
        owner, name = self._parse_repo(repo)
        url = f"https://api.github.com/repos/{owner}/{name}/releases"
        params = {"per_page": per_page}
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, list):
            return []
        releases: list[GitHubRelease] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            releases.append(self._parse_release(item))
        return releases

    async def download_asset(
        self,
        asset: GitHubReleaseAsset,
        *,
        start_byte: int = 0,
    ) -> httpx.Response:
        headers = self._headers()
        if start_byte > 0:
            headers["Range"] = f"bytes={start_byte}-"
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(asset.download_url, headers=headers)
            response.raise_for_status()
            return response

    @staticmethod
    def _parse_repo(repo: str) -> tuple[str, str]:
        token = repo.strip()
        if "/" not in token:
            raise ValueError("GitHub repo must be in owner/name format")
        owner, name = token.split("/", 1)
        if not owner or not name:
            raise ValueError("GitHub repo must be in owner/name format")
        return owner, name

    @staticmethod
    def _parse_release(item: dict[str, Any]) -> GitHubRelease:
        assets: list[GitHubReleaseAsset] = []
        for raw_asset in item.get("assets") or []:
            if not isinstance(raw_asset, dict):
                continue
            assets.append(
                GitHubReleaseAsset(
                    id=int(raw_asset.get("id") or 0),
                    name=str(raw_asset.get("name") or ""),
                    size=int(raw_asset.get("size") or 0),
                    download_url=str(raw_asset.get("browser_download_url") or ""),
                    content_type=str(raw_asset.get("content_type") or "application/octet-stream"),
                ),
            )
        return GitHubRelease(
            id=int(item.get("id") or 0),
            tag_name=str(item.get("tag_name") or ""),
            name=str(item.get("name") or ""),
            draft=bool(item.get("draft")),
            prerelease=bool(item.get("prerelease")),
            published_at=str(item.get("published_at") or ""),
            body=str(item.get("body") or ""),
            assets=assets,
            raw=item,
        )
