"""Alert system routes — rule management, incident lifecycle, evidence, and statistics."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.alert import (
    AlertRead,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    AlertStats,
)
from app.services.alerts.actions import AlertActionExecutor
from app.services.alerts.alert_service import AlertService
from app.services.alerts.auto_clip import AutoClipService
from app.services.alerts.evidence_bundle import EvidenceBundleService
from app.services.alerts.chain_of_custody import ChainOfCustodyService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# ------------------------------------------------------------------
# Alert Rule endpoints
# ------------------------------------------------------------------


@router.post("/rules", response_model=AlertRuleRead, status_code=201)
async def create_alert_rule(
    body: AlertRuleCreate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new alert rule."""
    rule = await AlertService.create_rule(
        db,
        name=body.name,
        conditions=body.conditions,
        actions=body.actions,
        workspace_id=workspace_id,
        enabled=body.enabled,
    )
    return rule


@router.get("/rules", response_model=list[AlertRuleRead])
async def list_alert_rules(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    db: AsyncSession = Depends(get_async_session),
):
    """List alert rules for a workspace."""
    return await AlertService.list_rules(db, workspace_id, enabled=enabled)


@router.get("/rules/{rule_id}", response_model=AlertRuleRead)
async def get_alert_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single alert rule."""
    try:
        return await AlertService.get_rule(db, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/rules/{rule_id}", response_model=AlertRuleRead)
async def update_alert_rule(
    rule_id: UUID,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update an alert rule."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        return await AlertService.update_rule(db, rule_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/rules/{rule_id}", response_model=AlertRuleRead)
async def delete_alert_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Soft-delete (disable) an alert rule."""
    try:
        return await AlertService.delete_rule(db, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------
# Alert endpoints
# ------------------------------------------------------------------


@router.get("", response_model=dict)
async def list_alerts(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """List alerts for a workspace with optional filters and pagination."""
    alerts, total = await AlertService.list_alerts(
        db, workspace_id, status=status, severity=severity, skip=skip, limit=limit,
    )
    return {
        "items": [AlertRead.model_validate(a).model_dump() for a in alerts],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats", response_model=AlertStats)
async def alert_stats(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get alert statistics for a workspace."""
    return await AlertService.get_alert_stats(db, workspace_id)


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(
    alert_id: UUID,
    user_id: UUID = Query(..., description="User acknowledging the alert"),
    db: AsyncSession = Depends(get_async_session),
):
    """Acknowledge an alert."""
    try:
        return await AlertService.acknowledge_alert(db, alert_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: UUID,
    user_id: UUID = Query(..., description="User resolving the alert"),
    db: AsyncSession = Depends(get_async_session),
):
    """Resolve an alert."""
    try:
        return await AlertService.resolve_alert(db, alert_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{alert_id}/dismiss", response_model=AlertRead)
async def dismiss_alert(
    alert_id: UUID,
    user_id: UUID = Query(..., description="User dismissing the alert"),
    db: AsyncSession = Depends(get_async_session),
):
    """Dismiss an alert."""
    try:
        return await AlertService.dismiss_alert(db, alert_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/test", response_model=AlertRead, status_code=201)
async def test_alert(
    rule_id: UUID = Query(..., description="Rule ID to test"),
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Trigger a test alert for a given rule."""
    try:
        rule = await AlertService.get_rule(db, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    alert = await AlertService.trigger_alert(
        db,
        rule_id=rule.id,
        severity="medium",
        payload={"test": True, "rule_name": rule.name, "message": "Test alert triggered manually"},
        workspace_id=workspace_id,
    )

    # Execute actions if configured
    actions_config = rule.actions if isinstance(rule.actions, list) else [rule.actions]
    await AlertActionExecutor.execute_actions(alert, actions_config)

    return alert


# ------------------------------------------------------------------
# Incident endpoints (aggregated alert views)
# ------------------------------------------------------------------


@router.get("/incidents", response_model=dict)
async def list_incidents(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    window_minutes: int = Query(30, description="Time window for grouping alerts into incidents"),
    db: AsyncSession = Depends(get_async_session),
):
    """Aggregated incident view: group alerts by rule + time window."""
    from datetime import timedelta
    from sqlalchemy import select
    from app.models.alert import Alert

    stmt = (
        select(Alert)
        .where(Alert.workspace_id == workspace_id)
        .order_by(Alert.created_at.desc())
    )
    result = await db.execute(stmt)
    alerts = list(result.scalars().all())

    # Group by rule_id and time window
    incidents: list[dict] = []
    used: set[UUID] = set()

    for alert in alerts:
        if alert.id in used:
            continue
        group = [alert]
        used.add(alert.id)
        for other in alerts:
            if other.id in used:
                continue
            if other.rule_id == alert.rule_id:
                if alert.created_at and other.created_at:
                    diff = abs((alert.created_at - other.created_at).total_seconds())
                    if diff <= window_minutes * 60:
                        group.append(other)
                        used.add(other.id)

        incident_id = str(group[0].id)
        incidents.append({
            "incident_id": incident_id,
            "rule_id": str(alert.rule_id),
            "alert_count": len(group),
            "severity": max(
                (a.severity.value if hasattr(a.severity, "value") else str(a.severity) for a in group),
                key=lambda s: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0),
            ),
            "first_alert_at": min(
                a.created_at.isoformat() for a in group if a.created_at
            ) if any(a.created_at for a in group) else None,
            "last_alert_at": max(
                a.created_at.isoformat() for a in group if a.created_at
            ) if any(a.created_at for a in group) else None,
            "alert_ids": [str(a.id) for a in group],
            "status": group[0].status.value if hasattr(group[0].status, "value") else str(group[0].status),
        })

    return {"incidents": incidents, "total": len(incidents)}


@router.get("/incidents/{incident_id}/timeline", response_model=dict)
async def incident_timeline(
    incident_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Chronological timeline for an incident (alerts + events + evidence)."""
    from sqlalchemy import select
    from app.models.alert import Alert

    result = await db.execute(select(Alert).where(Alert.id == incident_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    timeline_entries = [
        {
            "type": "alert",
            "timestamp": alert.created_at.isoformat() if alert.created_at else None,
            "data": AlertRead.model_validate(alert).model_dump(),
        }
    ]

    return {
        "incident_id": str(incident_id),
        "timeline": sorted(timeline_entries, key=lambda x: x.get("timestamp") or ""),
    }


@router.get("/incidents/{incident_id}/bundle", response_model=dict)
async def get_or_create_incident_bundle(
    incident_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get or create an evidence bundle for an incident."""
    bundle = await EvidenceBundleService.create_bundle(db, str(incident_id))
    return bundle


# ------------------------------------------------------------------
# Auto-clip endpoint
# ------------------------------------------------------------------


@router.post("/{alert_id}/auto-clip", response_model=dict, status_code=201)
async def trigger_auto_clip(
    alert_id: UUID,
    before_s: float = Query(10, description="Seconds before alert to capture"),
    after_s: float = Query(5, description="Seconds after alert to capture"),
    db: AsyncSession = Depends(get_async_session),
):
    """Trigger auto-clip capture for an alert."""
    clip_result = await AutoClipService.capture_clip_on_alert(
        alert_id=str(alert_id),
        before_s=before_s,
        after_s=after_s,
    )
    snapshot_result = await AutoClipService.create_snapshot_on_alert(
        alert_id=str(alert_id),
    )
    return {
        "clip": clip_result,
        "snapshot": snapshot_result,
    }


# ------------------------------------------------------------------
# Evidence bundle endpoints
# ------------------------------------------------------------------


@router.post("/{alert_id}/bundle", response_model=dict, status_code=201)
async def create_evidence_bundle(
    alert_id: UUID,
    case_id: Optional[str] = Query(None, description="Optional case/incident ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create an evidence bundle for an alert."""
    bundle = await EvidenceBundleService.create_bundle(
        db, str(alert_id), case_id=case_id,
    )
    return bundle


# ------------------------------------------------------------------
# Chain of custody endpoint
# ------------------------------------------------------------------


@router.get("/{alert_id}/custody", response_model=dict)
async def get_chain_of_custody(
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get chain of custody for an alert's evidence."""
    report = await ChainOfCustodyService.generate_custody_report(
        db, str(alert_id),
    )
    return report


# ------------------------------------------------------------------
# AL4 — Alert Rules Tab (stub endpoints with mock data)
# ------------------------------------------------------------------

import copy
from datetime import datetime as _dt
from uuid import uuid4 as _uuid4

_MOCK_AL4_RULES: list[dict] = [
    {
        "id": "a1b2c3d4-0001-4000-8000-000000000001",
        "name": "Low Confidence Detection",
        "severity": "warning",
        "conditions": [
            {"id": "c1", "field": "confidence", "operator": "<", "value": "0.5"},
        ],
        "logic_operator": "AND",
        "cooldown": "5m",
        "actions": {
            "email": {"enabled": True, "address": "alerts@example.com"},
            "slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"},
            "webhook": {"enabled": False, "post_url": ""},
            "auto_clip": True,
        },
        "enabled": True,
        "trigger_count": 12,
        "trigger_window_days": 7,
        "created_at": "2026-03-10T08:00:00Z",
        "updated_at": "2026-03-18T14:30:00Z",
    },
    {
        "id": "a1b2c3d4-0002-4000-8000-000000000002",
        "name": "Loud Audio + Motion Spike",
        "severity": "critical",
        "conditions": [
            {"id": "c2", "field": "audio_level", "operator": ">", "value": "85"},
            {"id": "c3", "field": "motion", "operator": ">", "value": "0.9"},
        ],
        "logic_operator": "AND",
        "cooldown": "15m",
        "actions": {
            "email": {"enabled": False, "address": ""},
            "slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/services/T00/B00/yyy"},
            "webhook": {"enabled": True, "post_url": "https://example.com/webhook"},
            "auto_clip": True,
        },
        "enabled": True,
        "trigger_count": 3,
        "trigger_window_days": 7,
        "created_at": "2026-03-12T10:00:00Z",
        "updated_at": "2026-03-19T09:15:00Z",
    },
    {
        "id": "a1b2c3d4-0003-4000-8000-000000000003",
        "name": "OCR Keyword Match",
        "severity": "info",
        "conditions": [
            {"id": "c4", "field": "ocr_text", "operator": "contains", "value": "RESTRICTED"},
        ],
        "logic_operator": "AND",
        "cooldown": "1h",
        "actions": {
            "email": {"enabled": True, "address": "security@example.com"},
            "slack": {"enabled": False, "webhook_url": ""},
            "webhook": {"enabled": False, "post_url": ""},
            "auto_clip": False,
        },
        "enabled": False,
        "trigger_count": 0,
        "trigger_window_days": 7,
        "created_at": "2026-03-15T12:00:00Z",
        "updated_at": "2026-03-15T12:00:00Z",
    },
]


@router.get("/rules/al4", response_model=list[dict])
async def list_al4_rules(
    workspace_id: UUID = Query(..., description="Workspace ID"),
):
    """List AL4 alert rules (stub with mock data)."""
    return _MOCK_AL4_RULES


@router.post("/rules/al4", response_model=dict, status_code=201)
async def create_al4_rule(
    body: dict,
    workspace_id: UUID = Query(..., description="Workspace ID"),
):
    """Create a new AL4 alert rule (stub)."""
    now = _dt.utcnow().isoformat() + "Z"
    new_rule = {
        "id": str(_uuid4()),
        **body,
        "trigger_count": 0,
        "trigger_window_days": 7,
        "created_at": now,
        "updated_at": now,
    }
    _MOCK_AL4_RULES.append(new_rule)
    return new_rule


@router.post("/rules/al4/{rule_id}/duplicate", response_model=dict, status_code=201)
async def duplicate_al4_rule(
    rule_id: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
):
    """Duplicate an existing AL4 alert rule (stub)."""
    source = next((r for r in _MOCK_AL4_RULES if r["id"] == rule_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    now = _dt.utcnow().isoformat() + "Z"
    dup = copy.deepcopy(source)
    dup["id"] = str(_uuid4())
    dup["name"] = f"{source['name']} (copy)"
    dup["trigger_count"] = 0
    dup["created_at"] = now
    dup["updated_at"] = now
    _MOCK_AL4_RULES.append(dup)
    return dup


@router.patch("/rules/al4/{rule_id}", response_model=dict)
async def toggle_al4_rule(
    rule_id: str,
    body: dict,
):
    """Toggle enabled state of an AL4 alert rule (stub)."""
    rule = next((r for r in _MOCK_AL4_RULES if r["id"] == rule_id), None)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    if "enabled" in body:
        rule["enabled"] = body["enabled"]
    rule["updated_at"] = _dt.utcnow().isoformat() + "Z"
    return rule


@router.delete("/rules/al4/{rule_id}", status_code=204)
async def delete_al4_rule(
    rule_id: str,
):
    """Delete an AL4 alert rule (stub)."""
    global _MOCK_AL4_RULES
    before = len(_MOCK_AL4_RULES)
    _MOCK_AL4_RULES = [r for r in _MOCK_AL4_RULES if r["id"] != rule_id]
    if len(_MOCK_AL4_RULES) == before:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return None


# ------------------------------------------------------------------
# Notification Channel endpoints
# ------------------------------------------------------------------


class SlackChannelConfig(BaseModel):
    webhook_url: str = ""
    channel_name: str = ""


class EmailChannelConfig(BaseModel):
    recipients: list[str] = Field(default_factory=list)
    subject_prefix: str = "[ALERT]"


class WebhookChannelConfig(BaseModel):
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    payload_template: str = ""


class NotificationChannelPayload(BaseModel):
    type: str  # "slack" | "email" | "webhook"
    enabled: bool = True
    severity_filter: list[str] = Field(default_factory=list)
    slack: Optional[SlackChannelConfig] = None
    email: Optional[EmailChannelConfig] = None
    webhook: Optional[WebhookChannelConfig] = None


@router.post("/channels/test", response_model=dict)
async def test_notification_channel(
    body: NotificationChannelPayload = Body(...),
):
    """Test a notification channel configuration (stub)."""
    return {"success": True, "message": "Test notification sent"}


@router.post("/channels", response_model=dict, status_code=201)
async def save_notification_channel(
    body: NotificationChannelPayload = Body(...),
):
    """Save a notification channel configuration (stub)."""
    return {
        "success": True,
        "channel": body.model_dump(),
    }
