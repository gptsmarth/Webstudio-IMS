"""Configurable password policy loaded from system settings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.password_history_repository import (
    PasswordHistoryRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.security.password import verify_password


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    min_length: int = 10
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_number: bool = True
    require_symbol: bool = False
    history_count: int = 5


class PasswordPolicyService:
    def __init__(self, session: AsyncSession) -> None:
        self._settings = SystemSettingRepository(session)
        self._history = PasswordHistoryRepository(session)

    async def get_policy(self) -> PasswordPolicy:
        return PasswordPolicy(
            min_length=await self._settings.get_int("password_min_length", default=10),
            require_uppercase=await self._settings.get_bool(
                "password_require_uppercase", default=True
            ),
            require_lowercase=await self._settings.get_bool(
                "password_require_lowercase", default=True
            ),
            require_number=await self._settings.get_bool("password_require_number", default=True),
            require_symbol=await self._settings.get_bool("password_require_symbol", default=False),
            history_count=await self._settings.get_int("password_history_count", default=5),
        )

    def validate_strength(self, password: str, policy: PasswordPolicy) -> None:
        if len(password) < policy.min_length:
            raise ValueError(f"Password must be at least {policy.min_length} characters")
        if policy.require_uppercase and not re.search(r"[A-Z]", password):
            raise ValueError("Password must include an uppercase letter")
        if policy.require_lowercase and not re.search(r"[a-z]", password):
            raise ValueError("Password must include a lowercase letter")
        if policy.require_number and not re.search(r"\d", password):
            raise ValueError("Password must include a number")
        if policy.require_symbol and not re.search(r"[^A-Za-z0-9]", password):
            raise ValueError("Password must include a special character")

    async def validate(self, password: str) -> PasswordPolicy:
        policy = await self.get_policy()
        self.validate_strength(password, policy)
        return policy

    async def ensure_not_reused(
        self, user_id: int, password: str, *, current_hash: str | None
    ) -> None:
        policy = await self.get_policy()
        if current_hash and verify_password(current_hash, password):
            raise ValueError("New password must be different from the current password")
        if await self._history.password_reused(
            user_id, password, history_count=policy.history_count
        ):
            raise ValueError("Password was used recently. Choose a different password.")

    async def record_password(self, user_id: int, password_hash: str) -> None:
        policy = await self.get_policy()
        await self._history.record_entry(user_id=user_id, password_hash=password_hash)
        await self._history.trim(user_id, keep=policy.history_count)

    @staticmethod
    def compliance_summary(policy: PasswordPolicy) -> dict[str, object]:
        rules = [
            f"Minimum {policy.min_length} characters",
        ]
        if policy.require_uppercase:
            rules.append("Uppercase letter")
        if policy.require_lowercase:
            rules.append("Lowercase letter")
        if policy.require_number:
            rules.append("Number")
        if policy.require_symbol:
            rules.append("Special character")
        if policy.history_count > 0:
            rules.append(f"Cannot reuse last {policy.history_count} passwords")
        return {
            "rules": rules,
            "history_count": policy.history_count,
        }
