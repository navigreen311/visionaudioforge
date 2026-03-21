"""Settings Audit Log API — mock audit trail entries."""

from __future__ import annotations

from fastapi import APIRouter, Query
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
) -> AuditLogResponse:
    """Return paginated, filterable audit log entries (mock data)."""
    filtered = list(MOCK_ENTRIES)

    if search:
        q = search.lower()
        filtered = [e for e in filtered if q in e.resource.lower() or q in str(e.details).lower()]

    if user:
        filtered = [e for e in filtered if e.user_name == user]

    if action:
        filtered = [e for e in filtered if e.action == action]

    if date_from:
        filtered = [e for e in filtered if e.timestamp >= date_from]

    if date_to:
        filtered = [e for e in filtered if e.timestamp <= date_to]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_entries = filtered[start:end]

    return AuditLogResponse(
        entries=page_entries,
        total=total,
        page=page,
        page_size=page_size,
    )
