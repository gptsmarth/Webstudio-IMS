"""SystemSetting persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.database.models.system_setting import SystemSetting
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class SystemSettingRepository(SqlAlchemyRepository[SystemSetting]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SystemSetting)

    async def get_by_key(self, setting_key: str) -> SystemSetting | None:
        result = await self._session.execute(
            select(SystemSetting).where(SystemSetting.setting_key == setting_key),
        )
        return result.scalar_one_or_none()

    async def get_bool(self, setting_key: str, *, default: bool = False) -> bool:
        setting = await self.get_by_key(setting_key)
        if setting is None:
            return default
        return setting.setting_value.lower() in {"true", "1", "yes"}

    async def get_string(self, setting_key: str) -> str | None:
        setting = await self.get_by_key(setting_key)
        return setting.setting_value if setting is not None else None

    async def get_int(self, setting_key: str, *, default: int) -> int:
        setting = await self.get_by_key(setting_key)
        if setting is None:
            return default
        return int(setting.setting_value)

    async def set_value(
        self,
        setting_key: str,
        value: str,
        *,
        value_type: SettingValueType,
        updated_by_user_id: int | None = None,
        description: str | None = None,
    ) -> SystemSetting:
        setting = await self.get_by_key(setting_key)
        if setting is None:
            setting = SystemSetting(
                setting_key=setting_key,
                setting_value=value,
                value_type=value_type,
                description=description,
                updated_by_user_id=updated_by_user_id,
            )
            return await self.add(setting)
        setting.setting_value = value
        setting.value_type = value_type
        setting.updated_by_user_id = updated_by_user_id
        if description is not None:
            setting.description = description
        await self._session.flush()
        await self._session.refresh(setting)
        return setting

    async def is_system_initialized(self) -> bool:
        return await self.get_bool("system_initialized", default=False)
