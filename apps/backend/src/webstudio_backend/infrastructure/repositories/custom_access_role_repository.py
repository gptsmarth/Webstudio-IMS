"""Custom access role persistence."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from webstudio_backend.infrastructure.database.models.custom_access_role import (
    CustomAccessRole,
    CustomAccessRolePermission,
)
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class CustomAccessRoleRepository(SqlAlchemyRepository[CustomAccessRole]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CustomAccessRole)

    async def get_by_id(self, role_id: int) -> CustomAccessRole | None:
        statement = (
            select(CustomAccessRole)
            .options(selectinload(CustomAccessRole.permissions))
            .where(CustomAccessRole.id == role_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> CustomAccessRole | None:
        statement = (
            select(CustomAccessRole)
            .options(selectinload(CustomAccessRole.permissions))
            .where(func.lower(CustomAccessRole.name) == name.strip().lower())
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[CustomAccessRole]:
        statement = (
            select(CustomAccessRole)
            .options(selectinload(CustomAccessRole.permissions))
            .where(CustomAccessRole.is_active.is_(True))
            .order_by(CustomAccessRole.name.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_all(self) -> list[CustomAccessRole]:
        statement = (
            select(CustomAccessRole)
            .options(selectinload(CustomAccessRole.permissions))
            .order_by(CustomAccessRole.name.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def permissions_for_role_id(self, role_id: int) -> list[str]:
        role = await self.get_by_id(role_id)
        if role is None or not role.is_active:
            return []
        return sorted(entry.permission for entry in role.permissions)

    async def count_users_assigned(self, role_id: int) -> int:
        statement = (
            select(func.count()).select_from(User).where(User.custom_access_role_id == role_id)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def create_role(
        self,
        *,
        name: str,
        description: str | None,
        permissions: set[str],
        actor_id: int,
    ) -> CustomAccessRole:
        role = CustomAccessRole(
            name=name.strip(),
            description=description.strip() if description else None,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
        role.permissions = [CustomAccessRolePermission(permission=p) for p in sorted(permissions)]
        return await self.add(role)

    async def update_role(
        self,
        role: CustomAccessRole,
        *,
        name: str | None,
        description: str | None,
        permissions: set[str] | None,
        is_active: bool | None,
        actor_id: int,
    ) -> CustomAccessRole:
        if name is not None:
            role.name = name.strip()
        if description is not None:
            role.description = description.strip() or None
        if is_active is not None:
            role.is_active = is_active
        if permissions is not None:
            role.permissions = [
                CustomAccessRolePermission(permission=p) for p in sorted(permissions)
            ]
        role.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(role, attribute_names=["permissions"])
        return role

    async def delete_role(self, role: CustomAccessRole) -> None:
        await self._session.delete(role)
        await self._session.flush()
