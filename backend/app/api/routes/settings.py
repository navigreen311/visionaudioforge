"""Settings API routes — user appearance preferences."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_identity
from app.database import get_async_session
from app.models.settings import AppearancePreference

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AppearancePreferences(BaseModel):
    theme: Literal["light", "dark", "system"] = "system"
    sidebar_width: Literal["compact", "normal", "wide"] = Field(
        default="normal", alias="sidebarWidth"
    )
    sidebar_auto_collapse: bool = Field(default=True, alias="sidebarAutoCollapse")
    dashboard_view: Literal["grid", "list"] = Field(
        default="grid", alias="dashboardView"
    )
    cards_per_row: Literal[0, 2, 3, 4] = Field(default=0, alias="cardsPerRow")
    language: str = "en"
    timezone: str = "UTC"
    date_format: Literal["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"] = Field(
        default="MM/DD/YYYY", alias="dateFormat"
    )
    time_format: Literal["12h", "24h"] = Field(default="12h", alias="timeFormat")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def _row_for(db: AsyncSession, request: Request) -> AppearancePreference | None:
    """Find the preference row belonging to the caller.

    Identity is resolved leniently: the console reaches this endpoint without a
    token today, and those callers share the one row with a NULL user_id rather
    than being rejected.
    """
    identity = get_identity(request)
    user_id = identity.user_id if identity is not None else None

    stmt = select(AppearancePreference)
    stmt = (
        stmt.where(AppearancePreference.user_id == user_id)
        if user_id is not None
        else stmt.where(AppearancePreference.user_id.is_(None))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/appearance", response_model=AppearancePreferences)
async def get_appearance(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> AppearancePreferences:
    """Return the current user's appearance preferences."""
    row = await _row_for(db, request)
    if row is None:
        return AppearancePreferences()
    return AppearancePreferences.model_validate(row.preferences)


@router.put("/appearance", response_model=AppearancePreferences)
async def update_appearance(
    payload: AppearancePreferences,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> AppearancePreferences:
    """Update the current user's appearance preferences."""
    row = await _row_for(db, request)
    if row is None:
        identity = get_identity(request)
        row = AppearancePreference(
            user_id=identity.user_id if identity is not None else None
        )
        db.add(row)

    # by_alias so the stored document uses the same camelCase keys the console
    # sends, and a round-trip through the DB returns exactly what was saved.
    row.preferences = payload.model_dump(by_alias=True)
    await db.commit()
    return payload
