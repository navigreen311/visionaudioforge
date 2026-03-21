"""Settings data routes — storage, audit log, and appearance preferences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

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


class AuditEntry(BaseModel):
    id: str
    user: str
    action: str
    target: str
    details: str
    ip: str
    timestamp: str


class AuditLogResponse(BaseModel):
    entries: list[AuditEntry] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 25


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


def _mock_audit_entries() -> list[AuditEntry]:
    """Return 15 mock audit log entries."""
    raw = [
        ("log-001", "admin@acme.io", "user.login", "session", "Login from Chrome/Win11", "10.0.1.5", "2026-03-20T09:00:00Z"),
        ("log-002", "jdoe@acme.io", "asset.upload", "ast-001", "Uploaded drone_survey_4k.mp4", "10.0.1.12", "2026-03-20T09:15:00Z"),
        ("log-003", "admin@acme.io", "settings.update", "appearance", "Changed theme to dark", "10.0.1.5", "2026-03-20T09:30:00Z"),
        ("log-004", "mchen@acme.io", "model.deploy", "model-v3", "Deployed to production", "10.0.2.8", "2026-03-20T10:00:00Z"),
        ("log-005", "jdoe@acme.io", "asset.delete", "ast-099", "Deleted obsolete scan", "10.0.1.12", "2026-03-20T10:20:00Z"),
        ("log-006", "admin@acme.io", "user.create", "mchen@acme.io", "Added new team member", "10.0.1.5", "2026-03-19T14:00:00Z"),
        ("log-007", "svc-pipeline", "pipeline.run", "pipe-42", "Nightly batch completed", "10.0.3.1", "2026-03-19T03:00:00Z"),
        ("log-008", "jdoe@acme.io", "annotation.save", "ann-512", "Saved 48 bounding boxes", "10.0.1.12", "2026-03-19T11:30:00Z"),
        ("log-009", "admin@acme.io", "role.update", "jdoe@acme.io", "Promoted to editor", "10.0.1.5", "2026-03-18T16:45:00Z"),
        ("log-010", "mchen@acme.io", "experiment.create", "exp-78", "Started A/B test", "10.0.2.8", "2026-03-18T13:00:00Z"),
        ("log-011", "svc-pipeline", "pipeline.fail", "pipe-41", "OOM during inference", "10.0.3.1", "2026-03-18T03:15:00Z"),
        ("log-012", "admin@acme.io", "backup.trigger", "storage", "Manual backup initiated", "10.0.1.5", "2026-03-17T22:00:00Z"),
        ("log-013", "jdoe@acme.io", "asset.download", "ast-005", "Downloaded satellite overlay", "10.0.1.12", "2026-03-17T10:10:00Z"),
        ("log-014", "mchen@acme.io", "model.retrain", "model-v2", "Retrain triggered", "10.0.2.8", "2026-03-17T08:30:00Z"),
        ("log-015", "admin@acme.io", "settings.update", "storage", "Increased quota to 20 GB", "10.0.1.5", "2026-03-16T17:00:00Z"),
    ]
    return [
        AuditEntry(id=r[0], user=r[1], action=r[2], target=r[3], details=r[4], ip=r[5], timestamp=r[6])
        for r in raw
    ]


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

_appearance: dict[str, Any] = AppearanceSettings().model_dump()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/storage", response_model=StorageResponse)
async def get_storage_info():
    """Return storage usage breakdown and largest assets."""
    return StorageResponse(largest_assets=_mock_largest_assets())


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    user: str = Query("", description="Filter by user email"),
    action: str = Query("", description="Filter by action type"),
    from_date: str = Query("", alias="from", description="Start date ISO"),
    to_date: str = Query("", alias="to", description="End date ISO"),
):
    """Return paginated audit log entries with optional filters.

    Filtering is acknowledged but returns the same mock data for now.
    """
    entries = _mock_audit_entries()

    # Apply basic filters on mock data so the API contract is exercised
    if user:
        entries = [e for e in entries if user.lower() in e.user.lower()]
    if action:
        entries = [e for e in entries if action.lower() in e.action.lower()]

    return AuditLogResponse(entries=entries, total=42, page=page, per_page=25)


@router.get("/appearance", response_model=AppearanceSettings)
async def get_appearance():
    """Return current appearance / UI preferences."""
    return AppearanceSettings(**_appearance)


@router.put("/appearance", response_model=AppearanceSettings)
async def update_appearance(body: AppearanceSettings):
    """Save appearance / UI preferences and return the updated values."""
    _appearance.update(body.model_dump())
    return AppearanceSettings(**_appearance)
