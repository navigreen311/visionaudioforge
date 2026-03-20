"""Mobile operator app routes — dashboard, alerts, push, sync, field notes."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.mobile.biometric_auth import BiometricAuthService
from app.services.mobile.field_annotation import FieldAnnotationService
from app.services.mobile.mobile_api import MobileAPIService
from app.services.mobile.offline_sync import OfflineSyncService
from app.services.mobile.push_notifications import PushNotificationService

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AcknowledgeRequest(BaseModel):
    user_id: UUID
    location: Optional[dict] = None


class SyncRequest(BaseModel):
    actions: list[dict]


class DeviceRegistration(BaseModel):
    user_id: UUID
    device_token: str
    platform: str  # 'ios' | 'android' | 'web'


class PushPreferencesUpdate(BaseModel):
    user_id: UUID
    preferences: dict


class FieldNoteRequest(BaseModel):
    workspace_id: UUID
    user_id: UUID
    content: str
    location: Optional[dict] = None
    attached_asset_id: Optional[str] = None


class BiometricRegister(BaseModel):
    user_id: str
    biometric_type: str


class BiometricVerify(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Dashboard & alerts
# ---------------------------------------------------------------------------


@router.get("/dashboard")
async def mobile_dashboard(
    workspace_id: UUID = Query(...),
    user_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Mobile-optimized dashboard with compact payload."""
    return await MobileAPIService.get_mobile_dashboard(db, workspace_id, user_id)


@router.get("/alerts")
async def mobile_alerts(
    workspace_id: UUID = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """Compact alert list with optional status filter and pagination."""
    return await MobileAPIService.get_mobile_alerts(
        db, workspace_id, status=status, limit=limit, offset=offset,
    )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    body: AcknowledgeRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Acknowledge an alert from mobile with optional location/photo."""
    return await MobileAPIService.acknowledge_mobile(
        db, alert_id, body.user_id, location=body.location,
    )


# ---------------------------------------------------------------------------
# Evidence upload
# ---------------------------------------------------------------------------


@router.post("/evidence")
async def upload_evidence(
    workspace_id: UUID = Query(...),
    user_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Upload field evidence from mobile device."""
    file_bytes = await file.read()
    metadata = {
        "filename": file.filename,
        "content_type": file.content_type,
    }
    return await MobileAPIService.upload_field_evidence(
        db, workspace_id, user_id, file_bytes, metadata,
    )


# ---------------------------------------------------------------------------
# Offline support
# ---------------------------------------------------------------------------


@router.get("/offline-package")
async def offline_package(
    workspace_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Download an offline data package for the workspace."""
    return await MobileAPIService.get_offline_package(db, workspace_id)


@router.post("/sync")
async def process_sync(
    body: SyncRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Process offline actions queued on the mobile device."""
    return await OfflineSyncService.process_offline_actions(db, body.actions)


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------


@router.post("/push/register")
async def register_push_device(
    body: DeviceRegistration,
    db: AsyncSession = Depends(get_async_session),
):
    """Register a device for push notifications."""
    return await PushNotificationService.register_device(
        db, body.user_id, body.device_token, body.platform,
    )


@router.post("/push/preferences")
async def update_push_preferences(
    body: PushPreferencesUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update push notification preferences."""
    return await PushNotificationService.update_preferences(
        db, body.user_id, body.preferences,
    )


# ---------------------------------------------------------------------------
# Field notes & photos
# ---------------------------------------------------------------------------


@router.post("/field-notes")
async def create_field_note(
    body: FieldNoteRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a field note with optional GPS location."""
    return await FieldAnnotationService.create_field_note(
        db,
        body.workspace_id,
        body.user_id,
        body.content,
        location=body.location,
        attached_asset_id=body.attached_asset_id,
    )


@router.post("/field-photos")
async def upload_field_photo(
    workspace_id: UUID = Query(...),
    user_id: UUID = Query(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Upload a field photo with notes and optional GPS location."""
    photo_bytes = await file.read()
    return await FieldAnnotationService.create_field_photo(
        db, workspace_id, user_id, photo_bytes, notes,
    )


@router.get("/field-notes")
async def list_field_notes(
    workspace_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """List field notes for a workspace."""
    return await FieldAnnotationService.get_field_notes(db, workspace_id)
