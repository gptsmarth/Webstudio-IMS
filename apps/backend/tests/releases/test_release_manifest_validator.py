"""Release manifest validation tests."""

from __future__ import annotations

from webstudio_backend.services.release_manifest_validator import (
    parse_checksums_file,
    validate_release_manifest,
)


def test_validate_release_manifest_accepts_minimal_valid_manifest() -> None:
    manifest = {
        "schema_version": "2.0.0",
        "release_version": "0.1.0",
        "build": {
            "timestamp": "2026-07-02T00:00:00+00:00",
            "git_commit": "abc123",
        },
        "components": {
            "backend": {
                "app_version": "0.1.0",
            },
        },
    }
    result = validate_release_manifest(manifest)
    assert result.valid is True
    assert result.errors == []


def test_validate_release_manifest_rejects_invalid_version() -> None:
    manifest = {
        "schema_version": "2.0.0",
        "release_version": "bad",
        "build": {"timestamp": "t", "git_commit": "c"},
        "components": {"backend": {"app_version": "0.1.0"}},
    }
    result = validate_release_manifest(manifest)
    assert result.valid is False
    assert any("release_version" in error for error in result.errors)


def test_parse_checksums_file() -> None:
    content = "abc123  artifacts/WEBSTUDIO Desktop Setup.exe\n"
    parsed = parse_checksums_file(content)
    assert parsed["WEBSTUDIO Desktop Setup.exe"] == "abc123"
