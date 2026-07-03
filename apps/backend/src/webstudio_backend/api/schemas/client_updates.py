"""Client update platform API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ClientUpdateArtifact(BaseModel):
    name: str
    sha256: str | None = None
    size_bytes: int | None = None
    download_url: str


class ClientUpdateCheckResponse(BaseModel):
    platform: str
    installed_version: str
    latest_version: str
    min_supported_version: str
    update_available: bool
    mandatory: bool
    release_channel: str
    release_notes: str | None = None
    published_at: str | None = None
    distribution_mode: Literal["installer", "apk_sideload", "app_store_notification"]
    app_store_url: str | None = None
    artifact: ClientUpdateArtifact | None = None
    github_contact_prohibited: bool = True
