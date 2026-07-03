"""Semantic version utilities tests."""

from __future__ import annotations

from webstudio_backend.services.release_semver import (
    compare_semver,
    is_valid_semver,
    normalize_tag,
    parse_build_number_from_version,
    parse_semver,
)


def test_normalize_tag_strips_v_prefix() -> None:
    assert normalize_tag("v0.1.0") == "0.1.0"


def test_is_valid_semver() -> None:
    assert is_valid_semver("0.1.0")
    assert is_valid_semver("v1.2.3")
    assert not is_valid_semver("not-a-version")


def test_compare_semver() -> None:
    assert compare_semver("0.2.0", "0.1.0") == 1
    assert compare_semver("0.1.0", "0.1.0") == 0
    assert compare_semver("0.1.0", "0.2.0") == -1


def test_parse_build_number_from_version() -> None:
    assert parse_build_number_from_version("0.1.0+1") == 1
    assert parse_build_number_from_version("0.1.0") == 1


def test_parse_semver_prerelease() -> None:
    parsed = parse_semver("1.0.0-beta.1")
    assert parsed is not None
    assert parsed.prerelease == "beta.1"
