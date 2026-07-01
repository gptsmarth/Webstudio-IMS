"""Custom access role administration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.permissions import (
    ASSIGNABLE_PERMISSIONS,
    normalize_permission_set,
    validate_assignable_permissions,
)
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.custom_access_role import CustomAccessRole
from webstudio_backend.infrastructure.repositories.custom_access_role_repository import (
    CustomAccessRoleRepository,
)


class CustomAccessRoleNotFoundError(Exception):
    def __init__(self, role_id: int) -> None:
        super().__init__(f"Access role {role_id} not found")
        self.role_id = role_id


class CustomAccessRoleInUseError(Exception):
    def __init__(self, role_id: int, user_count: int) -> None:
        super().__init__(f"Access role {role_id} is assigned to {user_count} user(s)")
        self.role_id = role_id
        self.user_count = user_count


class DuplicateAccessRoleNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Access role name '{name}' already exists")
        self.name = name


class CustomAccessRoleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = CustomAccessRoleRepository(session)
        self._recorder = AuditRecorder(session)

    async def list_roles(self, *, include_inactive: bool = False) -> list[CustomAccessRole]:
        if include_inactive:
            return await self._roles.list_all()
        return await self._roles.list_active()

    async def get_role(self, role_id: int) -> CustomAccessRole:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise CustomAccessRoleNotFoundError(role_id)
        return role

    def permission_catalog(self) -> list[str]:
        return list(ASSIGNABLE_PERMISSIONS)

    async def assigned_user_count(self, role_id: int) -> int:
        return await self._roles.count_users_assigned(role_id)

    async def create_role(
        self,
        *,
        name: str,
        description: str | None,
        permissions: list[str],
        actor: AuditActor,
    ) -> CustomAccessRole:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Role name is required")
        if await self._roles.get_by_name(cleaned_name) is not None:
            raise DuplicateAccessRoleNameError(cleaned_name)
        normalized = normalize_permission_set(set(permissions))
        validate_assignable_permissions(normalized)
        role = await self._roles.create_role(
            name=cleaned_name,
            description=description,
            permissions=normalized,
            actor_id=actor.user_id or 0,
        )
        await self._recorder.record_system_action(
            entity_type="custom_access_role",
            entity_id=str(role.id),
            actor=actor,
            description=f"Created access role '{role.name}'",
            new_value={"name": role.name, "permissions": sorted(normalized)},
        )
        return role

    async def update_role(
        self,
        role_id: int,
        *,
        name: str | None,
        description: str | None,
        permissions: list[str] | None,
        is_active: bool | None,
        actor: AuditActor,
    ) -> CustomAccessRole:
        role = await self.get_role(role_id)
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Role name is required")
            existing = await self._roles.get_by_name(cleaned)
            if existing is not None and existing.id != role.id:
                raise DuplicateAccessRoleNameError(cleaned)
        normalized = None
        if permissions is not None:
            normalized = normalize_permission_set(set(permissions))
            validate_assignable_permissions(normalized)
        updated = await self._roles.update_role(
            role,
            name=name.strip() if name is not None else None,
            description=description,
            permissions=normalized,
            is_active=is_active,
            actor_id=actor.user_id or 0,
        )
        assigned = await self._roles.count_users_assigned(role_id)
        if assigned > 0:
            await self._bump_assigned_users_token_version(role_id)
        await self._recorder.record_system_action(
            entity_type="custom_access_role",
            entity_id=str(updated.id),
            actor=actor,
            description=f"Updated access role '{updated.name}'",
            new_value={
                "name": updated.name,
                "is_active": updated.is_active,
                "permissions": sorted(entry.permission for entry in updated.permissions),
            },
        )
        return updated

    async def delete_role(self, role_id: int, *, actor: AuditActor) -> None:
        role = await self.get_role(role_id)
        assigned = await self._roles.count_users_assigned(role_id)
        if assigned > 0:
            raise CustomAccessRoleInUseError(role_id, assigned)
        name = role.name
        await self._roles.delete_role(role)
        await self._recorder.record_system_action(
            entity_type="custom_access_role",
            entity_id=str(role_id),
            actor=actor,
            description=f"Deleted access role '{name}'",
        )

    async def _bump_assigned_users_token_version(self, role_id: int) -> None:
        from sqlalchemy import update

        from webstudio_backend.infrastructure.database.models.user import User

        await self._session.execute(
            update(User)
            .where(User.custom_access_role_id == role_id)
            .values(token_version=User.token_version + 1),
        )
