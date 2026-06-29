"""Backup history search filters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BackupHistoryFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    backup_type: str | None = None
    trigger_type: str | None = None
    creator: str | None = None
    status: str | None = None
    include_archived: bool = True
