"""Resolve effective permissions for authenticated users."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.permissions import (
    normalize_permission_set,
    permissions_for_role,
)
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.custom_access_role_repository import (
    CustomAccessRoleRepository,
)


class PermissionResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._custom_roles = CustomAccessRoleRepository(session)

    async def resolve_for_user(self, user: User) -> list[str]:
        if user.role == UserRole.MAIN_ADMIN:
            return permissions_for_role(UserRole.MAIN_ADMIN)
        if user.custom_access_role_id is not None:
            raw = await self._custom_roles.permissions_for_role_id(user.custom_access_role_id)
            if raw:
                return sorted(normalize_permission_set(set(raw)))
        return permissions_for_role(user.role)
