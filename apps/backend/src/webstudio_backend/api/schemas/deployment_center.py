"""Deployment Center API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeploymentPackageItem(BaseModel):
    job_id: int
    tag_name: str
    release_version: str
    build_number: int
    status: str
    bundle_dir: str | None = None
    manifest_validated: bool = False
    checksums_verified: bool = False
    completed_at: str | None = None


class DeploymentCenterDashboard(BaseModel):
    current_version: str | None = None
    latest_version: str | None = None
    downloaded_version: str | None = None
    release_channel: str
    build_number: int | None = None
    git_commit: str | None = None
    git_short: str | None = None
    release_date: str | None = None
    compatibility_status: Literal["compatible", "update_available", "incompatible", "unknown"]
    downloaded_packages: list[DeploymentPackageItem] = Field(default_factory=list)
    deployment_status: str
    updates_root: str
    sync_enabled: bool = False
    github_repo: str = ""
    auto_deploy: bool = False


class DeploymentActionRequest(BaseModel):
    job_id: int | None = None
    administrator_approved: bool = False


class DeploymentEventItem(BaseModel):
    id: int
    event_type: str
    status: str
    release_version: str | None = None
    build_number: int | None = None
    release_channel: str | None = None
    job_id: int | None = None
    administrator_approved: bool
    performed_by_user_id: int | None = None
    error_message: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    completed_at: str | None = None


class DeploymentRunResponse(BaseModel):
    run_id: int
    job_id: int | None = None
    release_version: str
    build_number: int
    release_channel: str
    status: str
    current_step: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    pre_backup_run_id: int | None = None
    pre_backup_filename: str | None = None
    rollback_backup_run_id: int | None = None
    previous_release_id: int | None = None
    bundle_dir: str | None = None
    error_message: str | None = None
    performed_by_user_id: int | None = None
    created_at: str
    completed_at: str | None = None


class RollbackRunResponse(BaseModel):
    run_id: int
    status: str
    current_step: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    release_channel: str
    from_release_version: str
    from_build_number: int
    from_release_id: int | None = None
    to_release_version: str
    to_build_number: int
    to_release_id: int | None = None
    deployment_run_id: int | None = None
    deployment_event_id: int | None = None
    pre_rollback_backup_filename: str | None = None
    database_restore_filename: str | None = None
    health_status: dict[str, Any] = Field(default_factory=dict)
    permanent_history: bool = True
    error_message: str | None = None
    performed_by_user_id: int | None = None
    created_at: str
    completed_at: str | None = None


class RollbackHistoryResponse(BaseModel):
    items: list[RollbackRunResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    permanent_history: bool = True


class DeploymentEventHistoryResponse(BaseModel):
    items: list[DeploymentEventItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class DeploymentAnalyticsSummary(BaseModel):
    sync_enabled: bool = False
    last_github_sync_at: str | None = None
    last_github_sync_status: str | None = None
    pending_downloads: int = 0
    failed_downloads: int = 0
    deployment_run_counts: dict[str, int] = Field(default_factory=dict)
    rollback_total: int = 0
    failed_rollbacks: int = 0
    failed_deployments: int = 0
    retry_queue_size: int = 0


class DeploymentAnalyticsResponse(BaseModel):
    generated_at: str
    summary: DeploymentAnalyticsSummary
    release_downloads: dict[str, Any] = Field(default_factory=dict)
    deployment_history: list[dict[str, Any]] = Field(default_factory=list)
    deployment_runs: list[dict[str, Any]] = Field(default_factory=list)
    rollback_history: list[dict[str, Any]] = Field(default_factory=list)
    deployment_durations: list[dict[str, Any]] = Field(default_factory=list)
    health_check_history: list[dict[str, Any]] = Field(default_factory=list)
    desktop_version_distribution: list[dict[str, Any]] = Field(default_factory=list)
    mobile_version_distribution: list[dict[str, Any]] = Field(default_factory=list)
    deployment_failures: list[dict[str, Any]] = Field(default_factory=list)
    retry_queue: list[dict[str, Any]] = Field(default_factory=list)
    github_polling_history: dict[str, Any] = Field(default_factory=dict)
    scheduler_recovery: list[dict[str, Any]] = Field(default_factory=list)
    tally_scheduler_recovery: dict[str, Any] = Field(default_factory=dict)
    backup_scheduler_recovery: dict[str, Any] = Field(default_factory=dict)
