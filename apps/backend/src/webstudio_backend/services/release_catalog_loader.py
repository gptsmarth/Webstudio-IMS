"""Load enterprise release bundles from the on-disk release catalog."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease

SUPPORTED_PLATFORMS: list[dict[str, str]] = [
    {"id": "desktop_windows", "os": "windows", "artifact_key": "desktop_windows"},
    {"id": "desktop_macos", "os": "macos", "artifact_key": "desktop_macos"},
    {"id": "mobile_android", "os": "android", "artifact_key": "mobile_android"},
    {"id": "server_windows", "os": "windows", "artifact_key": "server_windows"},
]


def default_release_channel_for_env(app_env: str) -> ReleaseChannel:
    if app_env == "production":
        return ReleaseChannel.STABLE
    if app_env == "staging":
        return ReleaseChannel.BETA
    return ReleaseChannel.DEVELOPMENT


def parse_build_number(mobile_version: str, *, fallback: int = 1) -> int:
    match = re.search(r"\+(\d+)$", mobile_version.strip())
    if match:
        return int(match.group(1))
    return fallback


def parse_checksums_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, artifact_path = parts
        artifact_name = Path(artifact_path).name
        checksums[artifact_name] = digest
    return checksums


def build_compatibility_matrix(manifest: dict[str, Any]) -> dict[str, Any]:
    components = manifest.get("components") or {}
    backend = components.get("backend") or {}
    database = manifest.get("database") or {}
    release = manifest.get("release") or {}
    return {
        "desktop": {
            "min_version": backend.get("min_desktop_version")
            or manifest.get("release_version", "0.0.0"),
            "latest_version": (components.get("desktop") or {}).get("version"),
        },
        "mobile": {
            "min_version": backend.get("min_mobile_version")
            or manifest.get("release_version", "0.0.0"),
            "latest_version": (components.get("mobile_flutter") or {}).get("version"),
        },
        "server": {
            "min_version": backend.get("app_version") or manifest.get("release_version", "0.0.0"),
            "api_version": backend.get("api_version", "1.0"),
        },
        "database": {
            "alembic_head": database.get("alembic_head"),
            "min_alembic_head": release.get("min_alembic_head") or database.get("alembic_head"),
        },
        "min_client_version": backend.get("min_client_version"),
    }


def build_supported_platforms(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = manifest.get("artifacts") or {}
    platforms: list[dict[str, Any]] = []
    for entry in SUPPORTED_PLATFORMS:
        artifact_name = artifacts.get(entry["artifact_key"])
        if not artifact_name:
            continue
        platforms.append(
            {
                "id": entry["id"],
                "os": entry["os"],
                "artifact": artifact_name,
            },
        )
    return platforms


def release_from_bundle_dir(
    bundle_dir: Path,
    *,
    channel: ReleaseChannel,
    mark_current: bool,
) -> SoftwareRelease | None:
    manifest_path = bundle_dir / "version-manifest.json"
    if not manifest_path.is_file():
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build = manifest.get("build") or {}
    components = manifest.get("components") or {}
    mobile_version = str((components.get("mobile_flutter") or {}).get("version", ""))
    release_meta = manifest.get("release") or {}

    build_number = int(release_meta.get("build_number") or parse_build_number(mobile_version))
    channel_value = release_meta.get("channel")
    resolved_channel = (
        ReleaseChannel(channel_value)
        if channel_value in {item.value for item in ReleaseChannel}
        else channel
    )

    notes_path = bundle_dir / "RELEASE_NOTES.md"
    release_notes = notes_path.read_text(encoding="utf-8").strip() if notes_path.is_file() else None
    checksums = parse_checksums_file(bundle_dir / "checksums.sha256")

    timestamp_raw = build.get("timestamp")
    if timestamp_raw:
        build_timestamp = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00"))
    else:
        build_timestamp = datetime.now(UTC)

    return SoftwareRelease(
        release_version=str(manifest.get("release_version", "0.0.0")),
        build_number=build_number,
        release_channel=resolved_channel,
        git_commit=str(build.get("git_commit", "")),
        git_short=str(build.get("git_short", "")),
        build_timestamp=build_timestamp,
        release_notes=release_notes,
        manifest=manifest,
        checksums=checksums,
        compatibility_matrix=build_compatibility_matrix(manifest),
        supported_platforms=build_supported_platforms(manifest),
        is_current=mark_current,
        published_at=build_timestamp,
    )


def discover_bundle_dirs(catalog_root: Path) -> list[Path]:
    if not catalog_root.is_dir():
        return []
    dirs = [path for path in catalog_root.iterdir() if path.is_dir() and path.name.startswith("v")]
    return sorted(dirs, key=lambda path: path.name)
