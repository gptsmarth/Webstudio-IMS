"""User persistence repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import UserRole, UserStatus
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateUsernameError
from webstudio_backend.infrastructure.repositories.user_validation import normalize_username


class UserRepository(SqlAlchemyRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(self._model, user_id)

    async def get_by_username(self, username: str) -> User | None:
        normalized = normalize_username(username)
        result = await self._session.execute(
            select(User).where(User.username == normalized),
        )
        return result.scalar_one_or_none()

    async def count_by_role(self, role: UserRole, *, active_only: bool = True) -> int:
        statement = select(func.count()).select_from(User).where(User.role == role)
        if active_only:
            statement = statement.where(User.status == UserStatus.ACTIVE)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: UserRole,
        display_name: str | None = None,
        must_change_password: bool = False,
        created_by_user_id: int | None = None,
    ) -> User:
        normalized = normalize_username(username)
        if await self.get_by_username(normalized) is not None:
            raise DuplicateUsernameError(normalized)
        user = User(
            username=normalized,
            password_hash=password_hash,
            role=role,
            status=UserStatus.ACTIVE,
            display_name=display_name,
            must_change_password=must_change_password,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        return await self.add(user)

    async def list_users(
        self,
        page_params: PageParams,
        *,
        status: UserStatus | None = None,
        role: UserRole | None = None,
        search: str | None = None,
    ) -> PageResult[User]:
        statement: Select[tuple[User]] = select(User)
        if status is not None:
            statement = statement.where(User.status == status)
        if role is not None:
            statement = statement.where(User.role == role)
        if search:
            prefix = f"{search.strip()}%"
            statement = statement.where(
                or_(
                    User.username.ilike(prefix),
                    User.display_name.ilike(prefix),
                ),
            )
        statement = statement.order_by(User.username.asc())
        return await paginate(self._session, statement, page_params)

    async def update_display_name(self, user: User, display_name: str, *, actor_id: int) -> User:
        user.display_name = display_name
        user.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update_role(self, user: User, role: UserRole, *, actor_id: int) -> User:
        user.role = role
        user.updated_by_user_id = actor_id
        user.token_version += 1
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def set_password(
        self,
        user: User,
        password_hash: str,
        *,
        must_change_password: bool,
        actor_id: int | None,
    ) -> User:
        user.password_hash = password_hash
        user.must_change_password = must_change_password
        user.updated_by_user_id = actor_id
        user.token_version += 1
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def set_status(self, user: User, status: UserStatus, *, actor_id: int) -> User:
        user.status = status
        user.updated_by_user_id = actor_id
        if status == UserStatus.DISABLED:
            user.token_version += 1
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def record_failed_login(self, user: User, *, lockout_threshold: int, lockout_minutes: int) -> User:
        user.failed_login_count += 1
        if user.failed_login_count >= lockout_threshold:
            user.locked_until = datetime.now(UTC) + timedelta_from_minutes(lockout_minutes)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def record_successful_login(self, user: User) -> User:
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def clear_lockout(self, user: User) -> User:
        user.failed_login_count = 0
        user.locked_until = None
        await self._session.flush()
        await self._session.refresh(user)
        return user


def timedelta_from_minutes(minutes: int):
    from datetime import timedelta

    return timedelta(minutes=minutes)
