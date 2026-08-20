"""Settings data routes — storage, audit log, and appearance preferences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.settings import AppearancePreference

router = APIRouter(prefix="/api/settings", tags=["settings-data"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StorageByType(BaseModel):
    images_gb: float = 1.2
    audio_gb: float = 0.8
    video_gb: float = 0.3
    other_gb: float = 0.1


class LargestAsset(BaseModel):
    id: str
    name: str
    size_mb: float
    type: str
    uploaded_at: str


class StorageResponse(BaseModel):
    total_gb: float = 10
    used_gb: float = 2.4
    by_type: StorageByType = Field(default_factory=StorageByType)
    largest_assets: list[LargestAsset] = Field(default_factory=list)


class AppearanceSettings(BaseModel):
    theme: str = "light"
    sidebar_width: str = "normal"
    auto_collapse: bool = True
    default_view: str = "grid"
    cards_per_row: str = "auto"
    language: str = "en"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"


# ---------------------------------------------------------------------------
# Mock data builders
# ---------------------------------------------------------------------------

def _mock_largest_assets() -> list[LargestAsset]:
    """Return 10 mock largest-asset entries."""
    assets = [
        ("ast-001", "drone_survey_4k.mp4", 842.5, "video", "2026-03-15T10:30:00Z"),
        ("ast-002", "factory_panorama.png", 324.1, "image", "2026-03-14T08:15:00Z"),
        ("ast-003", "ambient_recording.wav", 256.8, "audio", "2026-03-13T14:20:00Z"),
        ("ast-004", "training_dataset.zip", 198.3, "archive", "2026-03-12T09:45:00Z"),
        ("ast-005", "satellite_overlay.tiff", 187.6, "image", "2026-03-11T16:00:00Z"),
        ("ast-006", "inspection_clip.mp4", 156.2, "video", "2026-03-10T11:30:00Z"),
        ("ast-007", "sensor_log_march.csv", 134.9, "data", "2026-03-09T07:00:00Z"),
        ("ast-008", "speech_sample_batch.flac", 112.4, "audio", "2026-03-08T13:10:00Z"),
        ("ast-009", "model_weights_v3.pt", 98.7, "model", "2026-03-07T20:45:00Z"),
        ("ast-010", "annotated_frames.tar", 87.1, "archive", "2026-03-06T15:30:00Z"),
    ]
    return [
        LargestAsset(id=a[0], name=a[1], size_mb=a[2], type=a[3], uploaded_at=a[4])
        for a in assets
    ]


# ---------------------------------------------------------------------------
# Storage
#
# Appearance was a module-level dict seeded from the Pydantic defaults, so a
# saved theme reverted on every restart. It reuses AppearancePreference, whose
# nullable user_id is the shared row for callers the console has not
# authenticated yet.
# ---------------------------------------------------------------------------


async def _appearance_row(db: AsyncSession) -> AppearancePreference | None:
    """The shared row for callers the console has not authenticated.

    user_id is nullable and Postgres does not treat NULLs as equal, so the
    unique constraint on it does not prevent a second shared row appearing.
    Take the oldest deterministically rather than letting scalar_one_or_none
    raise if one ever does.
    """
    result = await db.execute(
        select(AppearancePreference)
        .where(AppearancePreference.user_id.is_(None))
        .order_by(AppearancePreference.created_at)
        .limit(1)
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/storage", response_model=StorageResponse)
async def get_storage_info():
    """Return storage usage breakdown and largest assets."""
    return StorageResponse(largest_assets=_mock_largest_assets())


# NOTE: /api/settings/audit-log is served by routes/settings_audit.py. That
# module's entry shape (user_name / user_avatar / ip_address, dict details) and
# its query params (search, page_size, date_from, date_to) are what the
# console's AuditLogTab actually sends and reads; the variant that used to live
# here answered the same path with an incompatible shape.


@router.get("/appearance", response_model=AppearanceSettings)
async def get_appearance(db: AsyncSession = Depends(get_async_session)):
    """Return current appearance / UI preferences."""
    row = await _appearance_row(db)
    if row is None:
        return AppearanceSettings()
    # Defaults fill in any field added since the row was written.
    return AppearanceSettings(
        **{**AppearanceSettings().model_dump(), **(row.preferences or {})}
    )


@router.put("/appearance", response_model=AppearanceSettings)
async def update_appearance(
    body: AppearanceSettings,
    db: AsyncSession = Depends(get_async_session),
):
    """Save appearance / UI preferences and return the updated values."""
    row = await _appearance_row(db)
    if row is None:
        db.add(AppearancePreference(user_id=None, preferences=body.model_dump()))
    else:
        row.preferences = {**(row.preferences or {}), **body.model_dump()}

    await db.commit()
    return body
