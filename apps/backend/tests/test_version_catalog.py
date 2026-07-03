"""Version catalog loader tests (M13H)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from webstudio_backend.core.version_catalog import find_repo_root, load_version_catalog


def test_find_repo_root_from_backend_package() -> None:
    backend_root = Path(__file__).resolve().parents[1] / "src"
    repo = find_repo_root(backend_root)
    assert repo is not None
    assert (repo / "VERSION.json").is_file()


def test_load_version_catalog_matches_repo_file() -> None:
    catalog = load_version_catalog()
    repo = find_repo_root()
    assert repo is not None
    payload = json.loads((repo / "VERSION.json").read_text(encoding="utf-8"))
    assert catalog.version == payload["version"]
    assert catalog.build_number == payload["build_number"]
    assert catalog.release_channel == payload["release_channel"]
