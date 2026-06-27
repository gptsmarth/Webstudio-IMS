"""First-time system setup service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import SettingValueType, UserRole
from webstudio_backend.infrastructure.repositories.exceptions import (
    SetupPendingRecoveryConfirmationError,
    SystemAlreadyInitializedError,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.password import hash_password, validate_password_strength
from webstudio_backend.infrastructure.security.recovery_key import (
    generate_recovery_key,
    hash_recovery_key,
)


@dataclass(frozen=True, slots=True)
class SetupInitializeResult:
    user: object
    company_name: str
    recovery_key: str


class SetupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._users = UserRepository(session)
        self._recorder = AuditRecorder(session)

    async def get_status(self) -> dict[str, object]:
        initialized = await self._settings.is_system_initialized()
        company_name = await self._settings.get_string("company_name")
        main_admin = await self._users.get_main_admin()
        awaiting_recovery_confirmation = (
            not initialized
            and main_admin is not None
            and main_admin.recovery_key_hash is not None
        )
        return {
            "system_initialized": initialized,
            "company_name": company_name,
            "awaiting_recovery_key_confirmation": awaiting_recovery_confirmation,
        }

    async def initialize(
        self,
        *,
        company_name: str,
        main_admin_name: str,
        username: str,
        password: str,
        confirm_password: str,
    ) -> SetupInitializeResult:
        if await self._settings.is_system_initialized():
            raise SystemAlreadyInitializedError()
        if await self._users.get_main_admin() is not None:
            raise SetupPendingRecoveryConfirmationError()
        if password != confirm_password:
            raise ValueError("Password confirmation does not match")
        validate_password_strength(password)

        normalized_company = company_name.strip()
        if not normalized_company:
            raise ValueError("Company name is required")

        user = await self._users.create(
            username=username,
            password_hash=hash_password(password),
            role=UserRole.MAIN_ADMIN,
            display_name=main_admin_name.strip(),
            must_change_password=False,
        )
        recovery_key = generate_recovery_key()
        await self._users.set_recovery_key(user, hash_recovery_key(recovery_key))
        await self._settings.set_value(
            "company_name",
            normalized_company,
            value_type=SettingValueType.STRING,
            updated_by_user_id=user.id,
        )
        await self._recorder.record_recovery_key_generated(user, reason="initial_setup")
        return SetupInitializeResult(user=user, company_name=normalized_company, recovery_key=recovery_key)

    async def confirm_recovery_key(self) -> None:
        if await self._settings.is_system_initialized():
            raise SystemAlreadyInitializedError()
        main_admin = await self._users.get_main_admin()
        if main_admin is None or main_admin.recovery_key_hash is None:
            raise ValueError("Setup has not generated a recovery key yet")

        await self._settings.set_value(
            "system_initialized",
            "true",
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=main_admin.id,
        )
        company_name = await self._settings.get_string("company_name") or ""
        await self._recorder.record_system_initialize(
            company_name=company_name,
            main_admin_username=main_admin.username,
            user_id=main_admin.id,
        )
