"""Enterprise release management API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReleaseMetadataResponse(BaseModel):
    id: int | None = None
    release_version: str
    build_number: int
    release_channel: Literal["development", "beta", "stable"]
    git_commit: str
    git_short: str
    build_timestamp: str
    release_date: str | None = None
    database_revision: str | None = None
    release_notes: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    checksums: dict[str, str] = Field(default_factory=dict)
    compatibility_matrix: dict[str, Any] = Field(default_factory=dict)
    supported_platforms: list[dict[str, Any]] = Field(default_factory=list)
    is_current: bool = False
    published_at: str
    installed_on_server: bool | None = None
    source: str | None = None
    version_identity: dict[str, Any] | None = None


class ReleaseHistoryItem(BaseModel):
    id: int
    release_version: str
    build_number: int
    release_channel: Literal["development", "beta", "stable"]
    git_short: str
    build_timestamp: str
    is_current: bool
    published_at: str


class ReleaseHistoryResponse(BaseModel):
    channel: Literal["development", "beta", "stable"]
    items: list[ReleaseHistoryItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ReleaseSyncStatusResponse(BaseModel):
    enabled: bool
    github_repo: str
    polling_interval_seconds: int
    updates_root: str
    last_sync_at: str | None = None
    last_sync_status: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    queue_counts: dict[str, int] = Field(default_factory=dict)
    latest_completed: dict[str, Any] | None = None
    auto_deploy: bool = False


class ReleaseDownloadJobItem(BaseModel):
    id: int
    tag_name: str
    release_version: str
    build_number: int
    release_channel: Literal["development", "beta", "stable"]
    status: str
    bundle_dir: str | None = None
    manifest_validated: bool = False
    checksums_verified: bool = False
    attempt_count: int = 0
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    artifact_count: int = 0


class ReleaseDownloadHistoryResponse(BaseModel):
    items: list[ReleaseDownloadJobItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
