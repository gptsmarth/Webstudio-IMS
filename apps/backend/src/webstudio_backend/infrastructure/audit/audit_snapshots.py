"""Helpers for immutable audit value snapshots."""

from __future__ import annotations

import uuid
from typing import Any


def entity_ref(*, entity_id: int | str | uuid.UUID, name: str) -> dict[str, Any]:
    """Snapshot a referenced entity with id and human-readable name at write time."""
    return {"id": str(entity_id), "name": name}
