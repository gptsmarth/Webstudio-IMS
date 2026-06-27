"""Sorting helpers for repository queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import ColumnElement, Select, asc, desc

SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class SortParam:
    field: str
    direction: SortDirection = "asc"


def apply_sorting(
    statement: Select[tuple[object]],
    sort_params: list[SortParam],
    column_map: dict[str, ColumnElement[object]],
) -> Select[tuple[object]]:
    if not sort_params:
        return statement

    orderings: list[ColumnElement[object]] = []
    for sort_param in sort_params:
        column = column_map.get(sort_param.field)
        if column is None:
            raise ValueError(f"Unsupported sort field: {sort_param.field}")
        ordering = asc(column) if sort_param.direction == "asc" else desc(column)
        orderings.append(ordering)

    return statement.order_by(*orderings)
