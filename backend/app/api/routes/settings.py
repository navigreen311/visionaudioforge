"""Workspace settings routes: GET/PATCH settings, logo upload, export, delete."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RegionalSettings(BaseModel):
    timezone: str = "UTC"
    language: str = "en"
    date_format: str = Field("MM/DD/YYYY", alias="dateFormat")
    time_format: str = Field("12h", alias="timeFormat")

    model_config = {"populate_by_name": True}


class UsageLimitItem(BaseModel):
    used: int | float
    max: int | float
    unit: Optional[str] = None


class UsageLimits(BaseModel):
    api_calls: UsageLimitItem = Field(alias="apiCalls")
    storage: UsageLimitItem
    members: UsageLimitItem

    model_config = {"populate_by_name": True}


class WorkspaceInfo(BaseModel):
    id: str
    created_at: str = Field(alias="createdAt")
    region: str

    model_config = {"populate_by_name": True}


class WorkspaceSettingsRead(BaseModel):
    name: str
    description: str
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    accent_color: str = Field("#4F46E5", alias="accentColor")
    plan: str = "Free"
    limits: UsageLimits
    regional: RegionalSettings
    info: WorkspaceInfo

    model_config = {"populate_by_name": True}


class WorkspaceSettingsPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    accent_color: Optional[str] = Field(None, alias="accentColor")
    regional: Optional[RegionalSettings] = None

    model_config = {"populate_by_name": True}


class ExportResponse(BaseModel):
    export_id: str = Field(alias="exportId")
    status: str
    message: str

    model_config = {"populate_by_name": True}


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


# ---------------------------------------------------------------------------
# In-memory store (placeholder until wired to DB/service)
# ---------------------------------------------------------------------------

_MOCK_SETTINGS = WorkspaceSettingsRead(
    name="My Workspace",
    description="",
    logoUrl=None,
    accentColor="#4F46E5",
    plan="Free",
    limits=UsageLimits(
        apiCalls=UsageLimitItem(used=1240, max=5000),
        storage=UsageLimitItem(used=2.4, max=5, unit="GB"),
        members=UsageLimitItem(used=1, max=3),
    ),
    regional=RegionalSettings(
        timezone="UTC",
        language="en",
        dateFormat="MM/DD/YYYY",
        timeFormat="12h",
    ),
    info=WorkspaceInfo(
        id="ws_abc123def456",
        createdAt="2025-11-01T00:00:00Z",
        region="us-east-1",
    ),
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/workspace", response_model=WorkspaceSettingsRead)
async def get_workspace_settings() -> WorkspaceSettingsRead:
    """Return workspace settings for the current workspace."""
    return _MOCK_SETTINGS


@router.patch("/workspace", response_model=WorkspaceSettingsRead)
async def patch_workspace_settings(
    body: WorkspaceSettingsPatch,
) -> WorkspaceSettingsRead:
    """Partially update workspace settings."""
    global _MOCK_SETTINGS  # noqa: PLW0603
    data = _MOCK_SETTINGS.model_dump(by_alias=True)
    updates = body.model_dump(exclude_none=True, by_alias=True)
    if "regional" in updates and updates["regional"] is not None:
        data["regional"] = {**data["regional"], **updates.pop("regional")}
    data.update(updates)
    _MOCK_SETTINGS = WorkspaceSettingsRead(**data)
    return _MOCK_SETTINGS


@router.post("/workspace/logo")
async def upload_workspace_logo(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Upload a workspace logo image (PNG/JPEG, max 2MB)."""
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are accepted.")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 2MB limit.")
    # In production: save to object storage and return the URL
    fake_url = f"/uploads/logos/{uuid4().hex}.{file.filename or 'logo'}"
    return {"logoUrl": fake_url}


@router.post("/workspace/export", response_model=ExportResponse)
async def export_workspace_data() -> ExportResponse:
    """Initiate a workspace data export. Returns an export job ID."""
    export_id = uuid4().hex[:12]
    return ExportResponse(
        exportId=export_id,
        status="pending",
        message="Data export initiated. You will receive a download link when ready.",
    )


@router.delete("/workspace", response_model=DeleteResponse)
async def delete_workspace() -> DeleteResponse:
    """Permanently delete the workspace and all associated data."""
    # In production: require auth + typed confirmation
    return DeleteResponse(
        deleted=True,
        message="Workspace has been permanently deleted.",
    )
