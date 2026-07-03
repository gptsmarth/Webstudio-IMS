"""Resolve enterprise release update storage paths."""

from __future__ import annotations

import platform
from pathlib import Path

from webstudio_backend.core.config import Settings


def resolve_release_updates_root(settings: Settings) -> Path:
    configured = settings.release_updates_root.strip()
    if configured:
        return Path(configured)
    data_root = settings.webstudio_data_root.strip()
    if data_root:
        return Path(data_root) / "Updates"
    if platform.system() == "Windows":
        return Path(r"D:\WEBSTUDIO-IMS\Updates")
    return Path.cwd() / "updates"
