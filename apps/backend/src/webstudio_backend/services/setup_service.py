"""First-time system setup service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import SettingValueType, UserRole
from webstudio_backend.infrastructure.repositories.exceptions import SystemAlreadyInitializedError
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.password import hash_password, validate_password_strength


class SetupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._users = UserRepository(session)
        self._recorder = AuditRecorder(session)

    async def get_status(self) -> dict[str, object]:
        initialized = await self._settings.is_system_initialized()
        company_name = await self._settings.get_string("company_name")
        return {
            "system_initialized": initialized,
            "company_name": company_name,
        }

    async def initialize(
        self,
        *,
        company_name: str,
        main_admin_name: str,
        username: str,
        password: str,
        confirm_password: str,
    ):
        if await self._settings.is_system_initialized():
            raise SystemAlreadyInitializedError()
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
        await self._settings.set_value(
            "system_initialized",
            "true",
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=user.id,
        )
        await self._settings.set_value(
            "company_name",
            normalized_company,
            value_type=SettingValueType.STRING,
            updated_by_user_id=user.id,
        )
        await self._recorder.record_system_initialize(
            company_name=normalized_company,
            main_admin_username=user.username,
            user_id=user.id,
        )
        return user, normalized_company
