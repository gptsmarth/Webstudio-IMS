"""Main Admin password recovery service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.exceptions import (
    InvalidRecoveryKeyError,
    MainAdminNotFoundError,
    SystemNotInitializedError,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.password import hash_password, validate_password_strength
from webstudio_backend.infrastructure.security.recovery_key import (
    generate_recovery_key,
    hash_recovery_key,
    verify_recovery_key,
)


@dataclass(frozen=True, slots=True)
class MainAdminRecoveryResult:
    new_recovery_key: str


class MainAdminRecoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._recorder = AuditRecorder(session)

    async def recover_password(
        self,
        *,
        recovery_key: str,
        new_password: str,
        confirm_password: str,
    ) -> MainAdminRecoveryResult:
        if not await self._settings.is_system_initialized():
            raise SystemNotInitializedError()

        main_admin = await self._users.get_main_admin()
        if main_admin is None:
            raise MainAdminNotFoundError()
        if not verify_recovery_key(main_admin.recovery_key_hash, recovery_key):
            raise InvalidRecoveryKeyError()

        if new_password != confirm_password:
            raise ValueError("Password confirmation does not match")
        validate_password_strength(new_password)

        await self._recorder.record_recovery_key_used(main_admin)
        await self._users.mark_recovery_key_used(main_admin)

        await self._users.set_password(
            main_admin,
            hash_password(new_password),
            must_change_password=False,
            actor_id=main_admin.id,
        )
        await self._refresh_tokens.revoke_all_for_user(main_admin.id)
        await self._recorder.record_main_admin_password_recovered(main_admin)

        new_recovery_key = generate_recovery_key()
        await self._users.set_recovery_key(main_admin, hash_recovery_key(new_recovery_key))
        await self._recorder.record_recovery_key_regenerated(main_admin)

        return MainAdminRecoveryResult(new_recovery_key=new_recovery_key)

    @staticmethod
    def password_recovery_message_for_role(role: str | None) -> dict[str, object]:
        if role == "main_admin":
            return {
                "self_service_available": True,
                "message": "Use your Main Admin Recovery Key to reset the password.",
            }
        return {
            "self_service_available": False,
            "message": (
                "Password recovery is not available for this account. "
                "Contact your Main Administrator to reset your password."
            ),
        }
