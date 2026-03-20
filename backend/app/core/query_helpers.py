"""SQLAlchemy query helper utilities for pagination, filtering, and ordering."""

from __future__ import annotations

from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query


def paginate(query: Query, skip: int = 0, limit: int = 20) -> Query:
    """Apply offset/limit pagination to a SQLAlchemy query."""
    return query.offset(skip).limit(limit)


def apply_filters(query: Query, model: Any, filters: dict[str, Any]) -> Query:
    """Dynamically add WHERE clauses for each key/value in *filters*.

    Only attributes that exist on *model* are applied; unknown keys are
    silently ignored.
    """
    for field, value in filters.items():
        column = getattr(model, field, None)
        if column is not None:
            query = query.where(column == value)
    return query


def order_by_field(
    query: Query, model: Any, field: str, direction: str = "desc"
) -> Query:
    """Add an ORDER BY clause to *query*.

    Parameters
    ----------
    direction:
        ``"asc"`` or ``"desc"`` (default ``"desc"``).
    """
    column = getattr(model, field, None)
    if column is None:
        return query
    order_fn = asc if direction.lower() == "asc" else desc
    return query.order_by(order_fn(column))
