"""Actor context for audit log entries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditActor:
    user_id: int | None = None
    display_name: str = "System"
    role: str = "system"

    @classmethod
    def system(cls, *, display_name: str = "System", role: str = "system") -> AuditActor:
        return cls(display_name=display_name, role=role)
