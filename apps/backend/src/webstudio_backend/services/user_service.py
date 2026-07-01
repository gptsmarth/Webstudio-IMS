"""User management service."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import UserRole, UserStatus
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.repositories.exceptions import (
    LastMainAdminError,
    SelfMainAdminDisableError,
    UserNotFoundError,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import RefreshTokenRepository
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.repositories.custom_access_role_repository import (
    CustomAccessRoleRepository,
)
from webstudio_backend.infrastructure.repositories.user_validation import validate_human_role
from webstudio_backend.infrastructure.security.password import hash_password
from webstudio_backend.services.custom_access_role_service import CustomAccessRoleNotFoundError
from webstudio_backend.services.permission_resolver import PermissionResolver
from webstudio_backend.services.password_policy_service import PasswordPolicyService
from webstudio_backend.services.user_admin_service import UserAdminService


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._recorder = AuditRecorder(session)
        self._password_policy = PasswordPolicyService(session)

    async def list_users(
        self,
        page_params: PageParams,
        *,
        status: UserStatus | None = None,
        role: UserRole | None = None,
        search: str | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
        sort_field: str = "username",
        sort_direction: str = "asc",
    ) -> PageResult[User]:
        return await self._users.list_users(
            page_params,
            status=status,
            role=role,
            search=search,
            created_from=created_from,
            created_to=created_to,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )

    async def get_user(self, user_id: int) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def create_user(
        self,
        *,
        username: str,
        role: UserRole,
        temporary_password: str,
        display_name: str | None,
        actor: AuditActor,
    ) -> User:
        validate_human_role(role)
        await self._password_policy.validate(temporary_password)
        password_hash = hash_password(temporary_password)
        user = await self._users.create(
            username=username,
            password_hash=password_hash,
            role=role,
            display_name=display_name,
            must_change_password=True,
            created_by_user_id=actor.user_id,
        )
        await self._recorder.record_user_create(user, actor=actor)
        await self._password_policy.record_password(user.id, password_hash)
        return user

    async def update_display_name(
        self,
        user_id: int,
        *,
        display_name: str,
        actor: AuditActor,
    ) -> User:
        user = await self.get_user(user_id)
        old_name = user.display_name
        updated = await self._users.update_display_name(user, display_name, actor_id=actor.user_id or 0)
        await self._recorder.record_user_update(
            updated,
            field_name="display_name",
            old_value={"display_name": old_name},
            new_value={"display_name": display_name},
            actor=actor,
        )
        return updated

    async def update_role(self, user_id: int, *, role: UserRole, actor: AuditActor) -> User:
        validate_human_role(role)
        user = await self.get_user(user_id)
        if user.role == UserRole.MAIN_ADMIN and role != UserRole.MAIN_ADMIN:
            await self._ensure_not_last_main_admin(user)
        old_role = user.role.value
        updated = await self._users.update_role(user, role, actor_id=actor.user_id or 0)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_update(
            updated,
            field_name="role",
            old_value={"role": old_role},
            new_value={"role": role.value},
            actor=actor,
            description=f"Role changed from {old_role} to {role.value}",
        )
        return updated

    async def assign_access(
        self,
        user_id: int,
        *,
        access_type: str,
        role: UserRole | None,
        custom_role_id: int | None,
        actor: AuditActor,
    ) -> User:
        user = await self.get_user(user_id)
        if user.role == UserRole.MAIN_ADMIN:
            raise ValueError("Main Admin access cannot be customized")
        if access_type == "builtin":
            if role is None:
                raise ValueError("Built-in role is required")
            validate_human_role(role)
            if role == UserRole.MAIN_ADMIN:
                raise ValueError("Cannot assign Main Admin through access assignment")
            old_label = user.role.value
            updated = await self._users.update_access(
                user,
                role=role,
                custom_access_role_id=None,
                actor_id=actor.user_id or 0,
            )
            new_label = role.value
        else:
            if custom_role_id is None:
                raise ValueError("Custom access role is required")
            custom_role = await CustomAccessRoleRepository(self._session).get_by_id(custom_role_id)
            if custom_role is None or not custom_role.is_active:
                raise CustomAccessRoleNotFoundError(custom_role_id)
            old_label = user.role.value
            updated = await self._users.update_access(
                user,
                role=UserRole.SALESPERSON,
                custom_access_role_id=custom_role_id,
                actor_id=actor.user_id or 0,
            )
            new_label = custom_role.name
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_update(
            updated,
            field_name="access",
            old_value={"access": old_label},
            new_value={"access": new_label, "access_type": access_type},
            actor=actor,
            description=f"Access updated to {new_label}",
        )
        return updated

    async def reset_password(
        self,
        user_id: int,
        *,
        temporary_password: str,
        actor: AuditActor,
    ) -> User:
        user = await self.get_user(user_id)
        await self._password_policy.validate(temporary_password)
        await self._password_policy.ensure_not_reused(
            user_id,
            temporary_password,
            current_hash=user.password_hash,
        )
        password_hash = hash_password(temporary_password)
        updated = await self._users.set_password(
            user,
            password_hash,
            must_change_password=True,
            actor_id=actor.user_id,
        )
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._password_policy.record_password(user.id, password_hash)
        await self._recorder.record_user_update(
            updated,
            field_name="password",
            old_value={"password_reset": False},
            new_value={"password_reset": True},
            actor=actor,
            description=f"Password reset for user '{user.username}'",
        )
        return updated

    async def disable_user(self, user_id: int, *, actor: AuditActor) -> User:
        user = await self.get_user(user_id)
        if actor.user_id == user_id and user.role == UserRole.MAIN_ADMIN:
            raise SelfMainAdminDisableError()
        if user.role == UserRole.MAIN_ADMIN:
            await self._ensure_not_last_main_admin(user)
        updated = await self._users.set_status(user, UserStatus.DISABLED, actor_id=actor.user_id or 0)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_disable(updated, actor=actor)
        return updated

    async def enable_user(self, user_id: int, *, actor: AuditActor) -> User:
        user = await self.get_user(user_id)
        if user.archived_at is not None:
            raise ValueError("Archived users must be restored before activation")
        updated = await self._users.set_status(user, UserStatus.ACTIVE, actor_id=actor.user_id or 0)
        await self._recorder.record_user_enable(updated, actor=actor)
        return updated

    async def unlock_user(self, user_id: int, *, actor: AuditActor) -> User:
        user = await self.get_user(user_id)
        updated = await self._users.clear_lockout(user)
        await self._recorder.record_user_update(
            updated,
            field_name="lockout",
            old_value={"locked_until": user.locked_until.isoformat() if user.locked_until else None},
            new_value={"locked_until": None, "failed_login_count": 0},
            actor=actor,
            description=f"Account unlocked for user '{user.username}'",
        )
        return updated

    async def archive_user(self, user_id: int, *, actor: AuditActor) -> User:
        user = await self.get_user(user_id)
        if actor.user_id == user_id and user.role == UserRole.MAIN_ADMIN:
            raise SelfMainAdminDisableError()
        if user.role == UserRole.MAIN_ADMIN:
            await self._ensure_not_last_main_admin(user)
        if user.archived_at is not None:
            raise ValueError("User is already archived")
        updated = await self._users.archive(user, actor_id=actor.user_id or 0)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_archive(updated, actor=actor)
        return updated

    async def restore_user(self, user_id: int, *, actor: AuditActor) -> User:
        user = await self.get_user(user_id)
        if user.archived_at is None:
            raise ValueError("User is not archived")
        updated = await self._users.restore_from_archive(user, actor_id=actor.user_id or 0)
        await self._recorder.record_user_restore(updated, actor=actor)
        return updated

    async def force_logout_user(self, user_id: int, *, actor: AuditActor) -> int:
        user = await self.get_user(user_id)
        revoked = await UserAdminService(self._session).force_logout(user_id)
        await self._recorder.record_user_force_logout(user, actor=actor, sessions_revoked=revoked)
        return revoked

    async def _ensure_not_last_main_admin(self, user: User) -> None:
        if user.role != UserRole.MAIN_ADMIN:
            return
        count = await self._users.count_by_role(UserRole.MAIN_ADMIN, active_only=True)
        if count <= 1:
            raise LastMainAdminError()
