"""Semantic version parsing and comparison for enterprise releases."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$",
)


@dataclass(frozen=True, slots=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    @property
    def core(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def normalize_tag(tag_name: str) -> str:
    token = tag_name.strip()
    if token.lower().startswith("v"):
        return token[1:]
    return token


def parse_semver(value: str) -> SemanticVersion | None:
    token = normalize_tag(value)
    match = _SEMVER_RE.match(token)
    if match is None:
        return None
    return SemanticVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=match.group("prerelease") or "",
        build=match.group("build") or "",
    )


def is_valid_semver(value: str) -> bool:
    return parse_semver(value) is not None


def compare_semver(left: str, right: str) -> int:
    left_parsed = parse_semver(left)
    right_parsed = parse_semver(right)
    if left_parsed is None or right_parsed is None:
        raise ValueError("Invalid semantic version")
    if left_parsed.core != right_parsed.core:
        return -1 if left_parsed.core < right_parsed.core else 1
    if left_parsed.prerelease == right_parsed.prerelease:
        return 0
    if not left_parsed.prerelease:
        return 1
    if not right_parsed.prerelease:
        return -1
    return -1 if left_parsed.prerelease < right_parsed.prerelease else 1


def parse_build_number_from_version(version: str) -> int:
    parsed = parse_semver(version)
    if parsed is None or not parsed.build:
        return 1
    match = re.search(r"(\d+)$", parsed.build)
    return int(match.group(1)) if match else 1
