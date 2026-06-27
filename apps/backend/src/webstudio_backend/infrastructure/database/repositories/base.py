"""Generic repository interface and SQLAlchemy implementation."""

from __future__ import annotations

from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.database.repositories.sorting import (
    SortParam,
    apply_sorting,
)

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Protocol[ModelT]):
    async def get_by_id(self, entity_id: int) -> ModelT | None: ...

    async def add(self, entity: ModelT) -> ModelT: ...

    async def delete(self, entity: ModelT) -> None: ...

    async def list_all(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ModelT]: ...


class SqlAlchemyRepository(Repository[ModelT]):
    """Generic async repository for SQLAlchemy ORM models."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        return await self._session.get(self._model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def list_all(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ModelT]:
        statement = select(self._model)
        if sort_params:
            column_map = {column.key: column for column in self._model.__table__.columns}
            statement = apply_sorting(statement, sort_params, column_map)
        return await paginate(self._session, statement, page_params)
