"""Settings Audit Log API - reads the audit_logs table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_workspace_id
from app.models.audit_log import AuditLog
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    user_name: str
    user_avatar: str
    action: str
    resource: str
    details: dict[str, str | int | bool | None]
    ip_address: str


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_ENTRIES: list[AuditLogEntry] = [
    AuditLogEntry(
        id="aud-001",
        timestamp="2026-03-21T09:12:34Z",
        user_name="Alice Chen",
        user_avatar="AC",
        action="Create",
        resource="Pipeline: object-detection-v3",
        details={"pipeline_id": "pipe-882", "framework": "YOLOv8", "gpu_count": 2},
        ip_address="192.168.1.***",
    ),
    AuditLogEntry(
        id="aud-002",
        timestamp="2026-03-21T08:45:10Z",
        user_name="Bob Martinez",
        user_avatar="BM",
        action="Update",
        resource="Model: resnet50-finetuned",
        details={"field": "learning_rate", "old_value": "0.001", "new_value": "0.0005"},
        ip_address="10.0.0.***",
    ),
    AuditLogEntry(
        id="aud-003",
        timestamp="2026-03-21T08:30:00Z",
        user_name="Carol Davis",
        user_avatar="CD",
        action="Delete",
        resource="Dataset: noisy-audio-samples",
        details={"dataset_id": "ds-441", "record_count": 12400, "reason": "duplicate"},
        ip_address="172.16.5.***",
    ),
    AuditLogEntry(
        id="aud-004",
        timestamp="2026-03-21T07:55:22Z",
        user_name="Dan Kim",
        user_avatar="DK",
        action="Login",
        resource="Auth: SSO via Okta",
        details={"provider": "okta", "mfa": True, "session_id": "sess-8192"},
        ip_address="203.0.113.***",
    ),
    AuditLogEntry(
        id="aud-005",
        timestamp="2026-03-21T07:20:05Z",
        user_name="Eve Nguyen",
        user_avatar="EN",
        action="Export",
        resource="Report: weekly-metrics",
        details={"format": "CSV", "rows": 5200, "size_mb": 14},
        ip_address="192.168.2.***",
    ),
    AuditLogEntry(
        id="aud-006",
        timestamp="2026-03-20T18:10:33Z",
        user_name="Frank Li",
        user_avatar="FL",
        action="Install",
        resource="Plugin: spectral-augment-v2",
        details={"plugin_id": "plg-019", "version": "2.1.0", "auto_enabled": True},
        ip_address="10.10.3.***",
    ),
    AuditLogEntry(
        id="aud-007",
        timestamp="2026-03-20T16:42:11Z",
        user_name="Alice Chen",
        user_avatar="AC",
        action="Create",
        resource="Workspace: audio-research-lab",
        details={"workspace_id": "ws-773", "tier": "pro", "members": 5},
        ip_address="192.168.1.***",
    ),
    AuditLogEntry(
        id="aud-008",
        timestamp="2026-03-20T15:05:44Z",
        user_name="Grace Park",
        user_avatar="GP",
        action="Update",
        resource="Alert Rule: gpu-utilization-high",
        details={"threshold_old": 85, "threshold_new": 90, "channel": "slack"},
        ip_address="10.0.1.***",
    ),
    AuditLogEntry(
        id="aud-009",
        timestamp="2026-03-20T13:30:18Z",
        user_name="Henry Wu",
        user_avatar="HW",
        action="Delete",
        resource="API Key: dev-testing-key",
        details={"key_prefix": "vaf_test_****", "expired": True},
        ip_address="172.16.8.***",
    ),
    AuditLogEntry(
        id="aud-010",
        timestamp="2026-03-20T11:58:02Z",
        user_name="Bob Martinez",
        user_avatar="BM",
        action="Export",
        resource="Dataset: thermal-images-v4",
        details={"format": "COCO-JSON", "images": 8400, "size_mb": 340},
        ip_address="10.0.0.***",
    ),
    AuditLogEntry(
        id="aud-011",
        timestamp="2026-03-20T10:22:50Z",
        user_name="Ivy Torres",
        user_avatar="IT",
        action="Login",
        resource="Auth: password",
        details={"provider": "local", "mfa": False, "session_id": "sess-7201"},
        ip_address="198.51.100.***",
    ),
    AuditLogEntry(
        id="aud-012",
        timestamp="2026-03-19T22:14:09Z",
        user_name="Dan Kim",
        user_avatar="DK",
        action="Create",
        resource="Experiment: clip-audio-fusion-exp",
        details={"experiment_id": "exp-302", "base_model": "CLIP-ViT-B/32", "epochs": 50},
        ip_address="203.0.113.***",
    ),
    AuditLogEntry(
        id="aud-013",
        timestamp="2026-03-19T19:40:37Z",
        user_name="Carol Davis",
        user_avatar="CD",
        action="Update",
        resource="Pipeline: mel-spectrogram-extractor",
        details={"field": "hop_length", "old_value": "512", "new_value": "256"},
        ip_address="172.16.5.***",
    ),
    AuditLogEntry(
        id="aud-014",
        timestamp="2026-03-19T17:08:55Z",
        user_name="Eve Nguyen",
        user_avatar="EN",
        action="Install",
        resource="Plugin: faiss-gpu-index",
        details={"plugin_id": "plg-024", "version": "1.7.4", "index_type": "IVF+PQ"},
        ip_address="192.168.2.***",
    ),
    AuditLogEntry(
        id="aud-015",
        timestamp="2026-03-19T14:33:20Z",
        user_name="Frank Li",
        user_avatar="FL",
        action="Delete",
        resource="Stream: deprecated-rtsp-cam-7",
        details={"stream_id": "str-109", "uptime_hours": 0, "reason": "decommissioned"},
        ip_address="10.10.3.***",
    ),
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str = Query("", description="Free-text search across resource and details"),
    user: str = Query("", description="Filter by user name"),
    action: str = Query("", description="Filter by action type"),
    date_from: str = Query("", description="ISO date lower bound"),
    date_to: str = Query("", description="ISO date upper bound"),
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    """Paginated, filterable audit entries from `audit_logs`.

    This served a fixed list of fabricated entries, filtered and paginated in
    memory - so the compliance screen showed the same invented history to every
    workspace, and a real action never appeared in it. The AuditMiddleware has
    been writing genuine rows this whole time.
    """
    conditions = [AuditLog.workspace_id == session_workspace]

    if action:
        conditions.append(AuditLog.action == action)
    if search:
        pattern = f"%{search.lower()}%"
        conditions.append(
            or_(
                func.lower(AuditLog.resource).like(pattern),
                func.lower(AuditLog.action).like(pattern),
            )
        )
    for bound, op in ((date_from, "gte"), (date_to, "lte")):
        if not bound:
            continue
        try:
            parsed = datetime.fromisoformat(bound.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Not an ISO date: {bound!r}"
            ) from None
        conditions.append(
            AuditLog.timestamp >= parsed if op == "gte" else AuditLog.timestamp <= parsed
        )

    # The user filter is by name, but the column is a foreign key, so resolve it
    # rather than pretending the id is a name.
    if user:
        conditions.append(
            AuditLog.user_id.in_(
                select(User.id).where(func.lower(User.email).like(f"%{user.lower()}%"))
            )
        )

    total = int(
        (
            await db.execute(
                select(func.count()).select_from(AuditLog).where(*conditions)
            )
        ).scalar()
        or 0
    )

    rows = (
        (
            await db.execute(
                select(AuditLog, User.email)
                .join(User, User.id == AuditLog.user_id, isouter=True)
                .where(*conditions)
                .order_by(AuditLog.timestamp.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .all()
    )

    entries = [
        AuditLogEntry(
            id=str(row.AuditLog.id),
            timestamp=row.AuditLog.timestamp.isoformat() if row.AuditLog.timestamp else "",
            user_name=row.email or "system",
            # The console renders initials from this; derive them rather than
            # inventing an avatar URL that resolves to nothing.
            user_avatar=(row.email or "system")[:2].upper(),
            action=row.AuditLog.action,
            resource=row.AuditLog.resource,
            details={
                k: v
                for k, v in (row.AuditLog.payload or {}).items()
                if isinstance(v, (str, int, bool)) or v is None
            },
            ip_address=str((row.AuditLog.payload or {}).get("ip", "")),
        )
        for row in rows
    ]

    return AuditLogResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


