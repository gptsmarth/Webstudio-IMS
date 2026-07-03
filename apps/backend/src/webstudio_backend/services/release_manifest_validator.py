"""Validate enterprise release manifests and checksum catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from webstudio_backend.services.release_semver import is_valid_semver


@dataclass(slots=True)
class ManifestValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_release_manifest(manifest: dict[str, Any]) -> ManifestValidationResult:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ManifestValidationResult(valid=False, errors=["Manifest must be a JSON object"])

    release_version = str(manifest.get("release_version", "")).strip()
    if not release_version:
        errors.append("release_version is required")
    elif not is_valid_semver(release_version):
        errors.append(f"release_version '{release_version}' is not valid semver")

    schema_version = str(manifest.get("schema_version", "")).strip()
    if not schema_version:
        errors.append("schema_version is required")

    build = manifest.get("build")
    if not isinstance(build, dict):
        errors.append("build section is required")
    else:
        if not str(build.get("git_commit", "")).strip():
            errors.append("build.git_commit is required")
        if not str(build.get("timestamp", "")).strip():
            errors.append("build.timestamp is required")

    components = manifest.get("components")
    if not isinstance(components, dict):
        errors.append("components section is required")
    else:
        backend = components.get("backend")
        if not isinstance(backend, dict):
            errors.append("components.backend is required")
        else:
            app_version = str(backend.get("app_version", "")).strip()
            if not app_version:
                errors.append("components.backend.app_version is required")
            elif not is_valid_semver(app_version):
                errors.append(f"components.backend.app_version '{app_version}' is not valid semver")

    return ManifestValidationResult(valid=not errors, errors=errors)


def parse_checksums_file(content: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, artifact_path = parts
        artifact_name = artifact_path.rsplit("/", 1)[-1]
        checksums[artifact_name] = digest.lower()
    return checksums
