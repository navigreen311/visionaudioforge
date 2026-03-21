"""Settings API routes — user appearance preferences."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

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
# In-memory store (replace with DB persistence later)
# ---------------------------------------------------------------------------

_store: dict[str, AppearancePreferences] = {}

_DEFAULT_USER = "default"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/appearance", response_model=AppearancePreferences)
async def get_appearance() -> AppearancePreferences:
    """Return the current user's appearance preferences."""
    return _store.get(_DEFAULT_USER, AppearancePreferences())


@router.put("/appearance", response_model=AppearancePreferences)
async def update_appearance(payload: AppearancePreferences) -> AppearancePreferences:
    """Update the current user's appearance preferences."""
    _store[_DEFAULT_USER] = payload
    return payload
