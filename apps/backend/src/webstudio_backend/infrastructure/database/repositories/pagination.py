"""Pagination helpers for repository queries."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")
        if self.page_size > MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be <= {MAX_PAGE_SIZE}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class PageResult(Generic[T]):
    items: list[T]
    total_items: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 0
        return ceil(self.total_items / self.page_size)


def apply_pagination[T](statement: Select[tuple[T]], page_params: PageParams) -> Select[tuple[T]]:
    return statement.limit(page_params.page_size).offset(page_params.offset)


async def paginate[T](
    session: AsyncSession,
    statement: Select[tuple[T]],
    page_params: PageParams,
) -> PageResult[T]:
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total_result = await session.execute(count_statement)
    total_items = int(total_result.scalar_one())

    paginated_statement = apply_pagination(statement, page_params)
    result = await session.execute(paginated_statement)
    items = list(result.scalars().all())

    return PageResult(
        items=items,
        total_items=total_items,
        page=page_params.page,
        page_size=page_params.page_size,
    )
