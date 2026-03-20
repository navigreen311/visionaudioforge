"""Alert system routes — rule management, incident lifecycle, and statistics."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
