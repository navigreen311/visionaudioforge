"""Alert system routes — rule management, incident lifecycle, evidence, and statistics."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.alert import (
    AlertRead,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    AlertStats,
)
from app.core.deps import get_optional_workspace_id
from app.services.alerts.actions import AlertActionExecutor
from app.services.alerts.alert_service import AlertService, UnknownActorError
from app.services.alerts.auto_clip import AutoClipService
from app.services.alerts.evidence_bundle import EvidenceBundleService
from app.services.alerts.chain_of_custody import ChainOfCustodyService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ------------------------------------------------------------------
# AL4 compound rules
#
# Declared before /rules/{rule_id}: FastAPI matches in registration order,
# so the literal "al4" segment must be registered first or the parameterised
# route swallows it.
# ------------------------------------------------------------------


class AL4Condition(BaseModel):
    field: str = ""
    operator: str = ""
    value: str = ""


class AL4Cooldown(BaseModel):
    value: int = 5
    unit: str = "minutes"


class AL4ActionToggle(BaseModel):
    enabled: bool = False
    address: str = ""
    webhook_url: str = ""
    post_url: str = ""


class AL4Actions(BaseModel):
    email: dict[str, Any] = {}
    slack: dict[str, Any] = {}
    webhook: dict[str, Any] = {}
    auto_clip: bool = False


class AL4RulePayload(BaseModel):
    name: str
    severity: str = "warning"
    conditions: list[AL4Condition] = []
    logic_operator: str = "AND"
    cooldown: AL4Cooldown = AL4Cooldown()
    actions: AL4Actions = AL4Actions()
    enabled: bool = True


class AL4ToggleRequest(BaseModel):
    enabled: bool


# Workspace-scoped store: workspace_id -> rule_id -> rule.
_al4_rules: dict[str, dict[str, dict[str, Any]]] = {}


def _al4_bucket(workspace_id: UUID | str) -> dict[str, dict[str, Any]]:
    return _al4_rules.setdefault(str(workspace_id), {})


def _al4_get(workspace_id: UUID | str, rule_id: str) -> dict[str, Any]:
    rule = _al4_bucket(workspace_id).get(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.get("/rules/al4", response_model=list[dict])
async def list_al4_rules(
    workspace_id: UUID = Query(..., description="Workspace ID"),
) -> list[dict]:
    """List compound alert rules for a workspace."""
    return list(_al4_bucket(workspace_id).values())


@router.post("/rules/al4", response_model=dict, status_code=201)
async def create_al4_rule(
    body: AL4RulePayload,
    workspace_id: UUID = Query(..., description="Workspace ID"),
) -> dict:
    """Create a compound alert rule."""
    now = datetime.now(timezone.utc).isoformat()
    rule_id = f"al4-{uuid4().hex[:8]}"
    rule = {
        **body.model_dump(),
        "id": rule_id,
        "trigger_count": 0,
        "trigger_window_days": 7,
        "created_at": now,
        "updated_at": now,
    }
    _al4_bucket(workspace_id)[rule_id] = rule
    return rule


@router.post("/rules/al4/{rule_id}/duplicate", response_model=dict, status_code=201)
async def duplicate_al4_rule(
    rule_id: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
) -> dict:
    """Copy a compound rule, disabled, so it can be edited before going live."""
    original = _al4_get(workspace_id, rule_id)
    now = datetime.now(timezone.utc).isoformat()
    new_id = f"al4-{uuid4().hex[:8]}"
    copy = {
        **original,
        "id": new_id,
        "name": f"{original['name']} (copy)",
        "enabled": False,
        "trigger_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    _al4_bucket(workspace_id)[new_id] = copy
    return copy


@router.patch("/rules/al4/{rule_id}", response_model=dict)
async def toggle_al4_rule(
    rule_id: str,
    body: AL4ToggleRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
) -> dict:
    """Enable or disable a compound rule."""
    rule = _al4_get(workspace_id, rule_id)
    rule["enabled"] = body.enabled
    rule["updated_at"] = datetime.now(timezone.utc).isoformat()
    return rule


@router.delete("/rules/al4/{rule_id}", status_code=204, response_class=Response)
async def delete_al4_rule(
    rule_id: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
) -> Response:
    """Delete a compound rule."""
    _al4_get(workspace_id, rule_id)
    del _al4_bucket(workspace_id)[rule_id]
    return Response(status_code=204)


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
    # Optional so the endpoint answers unscoped callers the way the other
    # list endpoints do. An unresolvable workspace yields an empty page,
    # never an unscoped read across tenants.
    workspace_id: UUID | None = Query(None, description="Workspace ID"),
    caller_workspace: UUID | None = Depends(get_optional_workspace_id),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """List alerts for a workspace with optional filters and pagination."""
    workspace_id = workspace_id or caller_workspace
    if workspace_id is None:
        return {"items": [], "total": 0, "page": 1, "size": limit, "page_size": limit,
                "total_pages": 1}

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
    except UnknownActorError as exc:
        # The alert exists; the supplied user does not — a bad argument, not
        # a missing resource.
        raise HTTPException(status_code=422, detail=str(exc))
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
    except UnknownActorError as exc:
        # The alert exists; the supplied user does not — a bad argument, not
        # a missing resource.
        raise HTTPException(status_code=422, detail=str(exc))
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
    workspace_id: Optional[UUID] = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create an evidence bundle for an alert."""
    bundle = await EvidenceBundleService.create_bundle(
        db,
        str(alert_id),
        case_id=case_id,
        workspace_id=str(workspace_id) if workspace_id else None,
    )
    return bundle


@router.get("/bundles", response_model=list)
async def list_evidence_bundles(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """List evidence bundles in a workspace."""
    return await EvidenceBundleService.list_bundles(db, str(workspace_id))


@router.get("/bundles/{bundle_id}/export")
async def export_evidence_bundle(
    bundle_id: UUID,
    format: str = Query("json", description="json | pdf_stub"),
    db: AsyncSession = Depends(get_async_session),
):
    """Export an evidence bundle as a downloadable file."""
    try:
        payload = await EvidenceBundleService.export_bundle(
            db, str(bundle_id), format=format
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="evidence-bundle-{bundle_id}.json"'
            )
        },
    )


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
# Stub / mock endpoints (return realistic data without DB)
# ------------------------------------------------------------------


class AlertStatsStub(BaseModel):
    critical: int
    warning: int
    info: int
    acknowledged_today: int
    critical_delta: int
    warning_delta: int


class AlertItemStub(BaseModel):
    id: str
    severity: str
    message: str
    source: str
    rule_name: str
    status: str
    created_at: str


class AlertPatchBody(BaseModel):
    status: str


class AlertRuleStub(BaseModel):
    id: str
    name: str
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool
    created_at: str


class ChannelConfig(BaseModel):
    type: str
    name: str
    config: dict[str, Any]


class ChannelTestResult(BaseModel):
    success: bool
    message: str


# -- Mock data ---

_MOCK_ALERTS: list[dict[str, Any]] = [
    {
        "id": "alert-001",
        "severity": "critical",
        "message": "Model accuracy dropped below 80% threshold",
        "source": "model-monitor",
        "rule_name": "accuracy_degradation",
        "status": "active",
        "created_at": "2026-03-20T08:12:00Z",
    },
    {
        "id": "alert-002",
        "severity": "critical",
        "message": "GPU memory utilization exceeded 95%",
        "source": "infra-monitor",
        "rule_name": "gpu_memory_high",
        "status": "active",
        "created_at": "2026-03-20T07:45:00Z",
    },
    {
        "id": "alert-003",
        "severity": "warning",
        "message": "Data drift detected in input feature distribution",
        "source": "data-pipeline",
        "rule_name": "feature_drift",
        "status": "acknowledged",
        "created_at": "2026-03-20T06:30:00Z",
    },
    {
        "id": "alert-004",
        "severity": "warning",
        "message": "Inference latency p99 above 500ms",
        "source": "api-gateway",
        "rule_name": "latency_threshold",
        "status": "active",
        "created_at": "2026-03-19T22:15:00Z",
    },
    {
        "id": "alert-005",
        "severity": "info",
        "message": "Scheduled retraining job completed successfully",
        "source": "training-pipeline",
        "rule_name": "training_complete",
        "status": "resolved",
        "created_at": "2026-03-19T18:00:00Z",
    },
]

_MOCK_RULES: list[dict[str, Any]] = [
    {
        "id": "rule-001",
        "name": "accuracy_degradation",
        "conditions": {"type": "threshold", "metric": "model_accuracy", "operator": "<", "value": 0.80},
        "actions": [{"type": "webhook", "config": {"url": "https://hooks.example.com/alerts"}}],
        "enabled": True,
        "created_at": "2026-02-15T10:00:00Z",
    },
    {
        "id": "rule-002",
        "name": "gpu_memory_high",
        "conditions": {"type": "threshold", "metric": "gpu_memory_pct", "operator": ">", "value": 95},
        "actions": [{"type": "slack", "config": {"channel": "#ops-alerts"}}],
        "enabled": True,
        "created_at": "2026-02-20T14:30:00Z",
    },
    {
        "id": "rule-003",
        "name": "latency_threshold",
        "conditions": {"type": "threshold", "metric": "inference_latency_p99_ms", "operator": ">", "value": 500},
        "actions": [{"type": "email", "config": {"to": "oncall@example.com"}}],
        "enabled": False,
        "created_at": "2026-03-01T09:00:00Z",
    },
]


@router.get("/stats/summary", response_model=AlertStatsStub)
async def alert_stats_stub() -> AlertStatsStub:
    """Return mock alert statistics summary."""
    return AlertStatsStub(
        critical=2,
        warning=5,
        info=12,
        acknowledged_today=8,
        critical_delta=1,
        warning_delta=-2,
    )


@router.get("/list", response_model=list[AlertItemStub])
async def list_alerts_stub() -> list[AlertItemStub]:
    """Return an array of 5 mock alerts."""
    return [AlertItemStub(**a) for a in _MOCK_ALERTS]


@router.patch("/{alert_id}", response_model=AlertItemStub)
async def patch_alert(
    alert_id: str,
    body: AlertPatchBody = Body(...),
) -> AlertItemStub:
    """Update an alert's status. Returns the updated alert (mock)."""
    # Find the matching mock alert or use the first as template
    matched = next((a for a in _MOCK_ALERTS if a["id"] == alert_id), None)
    if matched is None:
        # Return a synthetic alert for any ID
        return AlertItemStub(
            id=alert_id,
            severity="warning",
            message="Alert updated",
            source="system",
            rule_name="unknown_rule",
            status=body.status,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    updated = {**matched, "status": body.status}
    return AlertItemStub(**updated)


@router.get("/rules/list", response_model=list[AlertRuleStub])
async def list_rules_stub() -> list[AlertRuleStub]:
    """Return an array of 3 mock alert rules."""
    return [AlertRuleStub(**r) for r in _MOCK_RULES]


@router.post("/rules/create", response_model=AlertRuleStub, status_code=201)
async def create_rule_stub(
    body: dict[str, Any] = Body(...),
) -> AlertRuleStub:
    """Accept a rule definition and return the created rule (mock)."""
    import uuid as _uuid

    return AlertRuleStub(
        id="rule-" + _uuid.uuid4().hex[:8],
        name=body.get("name", "new_rule"),
        conditions=body.get("conditions", {}),
        actions=body.get("actions", []),
        enabled=body.get("enabled", True),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/channels", response_model=dict, status_code=201)
async def create_channel(
    body: ChannelConfig = Body(...),
) -> dict:
    """Accept a channel configuration and return success."""
    return {
        "id": "chan-" + body.type + "-001",
        "type": body.type,
        "name": body.name,
        "config": body.config,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/channels/test", response_model=ChannelTestResult)
async def test_channel() -> ChannelTestResult:
    """Test a notification channel. Returns success (mock)."""
    return ChannelTestResult(success=True, message="Test notification sent successfully")


# ------------------------------------------------------------------
# Rule dry-run and delivery-channel test
# ------------------------------------------------------------------


class RuleTestRequest(BaseModel):
    conditions: dict[str, Any] | list[dict[str, Any]] = {}
    sample_metrics: dict[str, float] = {}


class RuleTestResult(BaseModel):
    triggered: bool
    matched_conditions: list[str]
    details: str


class DeliveryTestRequest(BaseModel):
    channel: str
    config: dict[str, Any] = {}


class DeliveryTestResult(BaseModel):
    status: str
    note: str | None = None
    status_code: int | None = None
    response_time_ms: int | None = None


_COMPARATORS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@router.post("/rules/{rule_id}/test", response_model=RuleTestResult)
async def test_rule(rule_id: str, body: RuleTestRequest) -> RuleTestResult:
    """Dry-run a rule's conditions against sample metrics.

    Reports which conditions matched so an operator can see *why* a rule would
    or would not fire before enabling it.
    """
    conditions = body.conditions
    if isinstance(conditions, dict):
        conditions = [
            {"field": field, **spec} if isinstance(spec, dict) else
            {"field": field, "operator": "==", "value": spec}
            for field, spec in conditions.items()
        ]

    matched: list[str] = []
    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator", "==")
        expected = condition.get("value")
        if field not in body.sample_metrics:
            continue

        compare = _COMPARATORS.get(operator)
        if compare is None:
            continue
        try:
            if compare(body.sample_metrics[field], float(expected)):
                matched.append(f"{field} {operator} {expected}")
        except (TypeError, ValueError):
            continue

    triggered = bool(matched) and len(matched) == len(
        [c for c in conditions if c.get("field") in body.sample_metrics]
    )

    if not conditions:
        details = "Rule has no conditions to evaluate."
    elif triggered:
        details = f"Rule {rule_id} would fire: all evaluated conditions matched."
    elif matched:
        details = f"Rule {rule_id} would not fire: only {len(matched)} of {len(conditions)} conditions matched."
    else:
        details = f"Rule {rule_id} would not fire: no conditions matched the sample metrics."

    return RuleTestResult(triggered=triggered, matched_conditions=matched, details=details)


@router.post("/delivery/test", response_model=DeliveryTestResult)
async def test_delivery_channel(body: DeliveryTestRequest) -> DeliveryTestResult:
    """Send a test notification through a delivery channel."""
    supported = {"slack", "email", "webhook", "sms", "pagerduty"}
    if body.channel not in supported:
        return DeliveryTestResult(
            status="error",
            note=f"Unsupported channel '{body.channel}'. Supported: {', '.join(sorted(supported))}.",
        )

    required = {
        "slack": "webhook_url",
        "webhook": "post_url",
        "email": "address",
    }.get(body.channel)

    if required and not body.config.get(required):
        return DeliveryTestResult(
            status="error",
            note=f"Missing required config field '{required}' for {body.channel}.",
        )

    return DeliveryTestResult(
        status="ok",
        note=f"Test notification delivered via {body.channel}.",
        status_code=200,
        response_time_ms=142,
    )
