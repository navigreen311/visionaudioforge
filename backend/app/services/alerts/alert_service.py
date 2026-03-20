"""AlertService — CRUD for alert rules and incident lifecycle management."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertRule, AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)


class AlertService:
    """Manages alert rules and alert lifecycle (create, ack, resolve, dismiss)."""

    # ------------------------------------------------------------------
    # Alert Rule CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_rule(
        db: AsyncSession,
        name: str,
        conditions: dict[str, Any],
        actions: list[dict[str, Any]],
        workspace_id: UUID,
        enabled: bool = True,
    ) -> AlertRule:
        """Create a new alert rule."""
        rule = AlertRule(
            name=name,
            conditions=conditions,
            actions=actions,
            workspace_id=workspace_id,
            enabled=enabled,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        logger.info("Created alert rule %s '%s' for workspace %s", rule.id, name, workspace_id)
        return rule

    @staticmethod
    async def list_rules(
        db: AsyncSession,
        workspace_id: UUID,
        enabled: Optional[bool] = None,
    ) -> list[AlertRule]:
        """List alert rules for a workspace, optionally filtering by enabled status."""
        stmt = select(AlertRule).where(AlertRule.workspace_id == workspace_id)
        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)
        stmt = stmt.order_by(AlertRule.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_rule(db: AsyncSession, rule_id: UUID) -> AlertRule:
        """Get a single alert rule by ID. Raises ValueError if not found."""
        result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise ValueError(f"Alert rule {rule_id} not found")
        return rule

    @staticmethod
    async def update_rule(db: AsyncSession, rule_id: UUID, **kwargs: Any) -> AlertRule:
        """Update an alert rule. Raises ValueError if not found."""
        result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise ValueError(f"Alert rule {rule_id} not found")
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        await db.commit()
        await db.refresh(rule)
        logger.info("Updated alert rule %s", rule_id)
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, rule_id: UUID) -> AlertRule:
        """Soft-delete an alert rule by disabling it."""
        result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise ValueError(f"Alert rule {rule_id} not found")
        rule.enabled = False
        await db.commit()
        await db.refresh(rule)
        logger.info("Soft-deleted (disabled) alert rule %s", rule_id)
        return rule

    # ------------------------------------------------------------------
    # Rule evaluation
    # ------------------------------------------------------------------

    @staticmethod
    async def evaluate_rule(
        db: AsyncSession,
        rule: AlertRule,
        metric_value: float,
    ) -> Optional[Alert]:
        """Evaluate a rule against a metric value. Create an Alert if triggered.

        Condition format:
        {"type": "threshold"|"compound"|"temporal",
         "metric": str, "operator": ">"|"<"|"=="|"!=",
         "value": float, "window_seconds": int|None}
        """
        conditions = rule.conditions
        operator = conditions.get("operator", "==")
        threshold = conditions.get("value", 0)

        triggered = False
        if operator == ">" and metric_value > threshold:
            triggered = True
        elif operator == "<" and metric_value < threshold:
            triggered = True
        elif operator == "==" and metric_value == threshold:
            triggered = True
        elif operator == "!=" and metric_value != threshold:
            triggered = True

        if not triggered:
            return None

        # Determine severity based on how far the value exceeds the threshold
        if operator in (">", "<"):
            diff_ratio = abs(metric_value - threshold) / max(abs(threshold), 1)
            if diff_ratio > 2.0:
                severity = AlertSeverity.critical
            elif diff_ratio > 1.0:
                severity = AlertSeverity.high
            elif diff_ratio > 0.5:
                severity = AlertSeverity.medium
            else:
                severity = AlertSeverity.low
        else:
            severity = AlertSeverity.medium

        payload = {
            "metric": conditions.get("metric", "unknown"),
            "metric_value": metric_value,
            "threshold": threshold,
            "operator": operator,
            "rule_name": rule.name,
        }

        alert = await AlertService.trigger_alert(
            db,
            rule_id=rule.id,
            severity=severity,
            payload=payload,
            workspace_id=rule.workspace_id,
        )
        return alert

    # ------------------------------------------------------------------
    # Alert lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    async def trigger_alert(
        db: AsyncSession,
        rule_id: UUID,
        severity: AlertSeverity | str,
        payload: dict[str, Any],
        workspace_id: UUID,
    ) -> Alert:
        """Create a new alert record."""
        if isinstance(severity, str):
            severity = AlertSeverity(severity)
        alert = Alert(
            rule_id=rule_id,
            severity=severity,
            payload=payload,
            status=AlertStatus.new,
            workspace_id=workspace_id,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        logger.info("Triggered alert %s (severity=%s, rule=%s)", alert.id, severity.value, rule_id)
        return alert

    @staticmethod
    async def list_alerts(
        db: AsyncSession,
        workspace_id: UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Alert], int]:
        """List alerts for a workspace with optional filters and pagination."""
        base = select(Alert).where(Alert.workspace_id == workspace_id)
        if status is not None:
            base = base.where(Alert.status == AlertStatus(status))
        if severity is not None:
            base = base.where(Alert.severity == AlertSeverity(severity))

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated results
        stmt = base.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        alerts = list(result.scalars().all())
        return alerts, total

    @staticmethod
    async def _transition_alert(
        db: AsyncSession,
        alert_id: UUID,
        user_id: UUID,
        new_status: AlertStatus,
    ) -> Alert:
        """Transition an alert to a new status."""
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert is None:
            raise ValueError(f"Alert {alert_id} not found")
        alert.status = new_status
        alert.acknowledged_by = user_id
        await db.commit()
        await db.refresh(alert)
        logger.info("Alert %s transitioned to %s by user %s", alert_id, new_status.value, user_id)
        return alert

    @staticmethod
    async def acknowledge_alert(db: AsyncSession, alert_id: UUID, user_id: UUID) -> Alert:
        """Acknowledge an alert."""
        return await AlertService._transition_alert(db, alert_id, user_id, AlertStatus.acknowledged)

    @staticmethod
    async def resolve_alert(db: AsyncSession, alert_id: UUID, user_id: UUID) -> Alert:
        """Resolve an alert."""
        return await AlertService._transition_alert(db, alert_id, user_id, AlertStatus.resolved)

    @staticmethod
    async def dismiss_alert(db: AsyncSession, alert_id: UUID, user_id: UUID) -> Alert:
        """Dismiss an alert."""
        return await AlertService._transition_alert(db, alert_id, user_id, AlertStatus.dismissed)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @staticmethod
    async def get_alert_stats(db: AsyncSession, workspace_id: UUID) -> dict[str, Any]:
        """Return aggregate alert statistics for a workspace."""
        base = select(Alert).where(Alert.workspace_id == workspace_id)

        # Total count
        total = (await db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar() or 0

        # By severity
        sev_stmt = (
            select(Alert.severity, func.count())
            .where(Alert.workspace_id == workspace_id)
            .group_by(Alert.severity)
        )
        sev_result = await db.execute(sev_stmt)
        by_severity = {row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in sev_result.all()}

        # By status
        stat_stmt = (
            select(Alert.status, func.count())
            .where(Alert.workspace_id == workspace_id)
            .group_by(Alert.status)
        )
        stat_result = await db.execute(stat_stmt)
        by_status = {row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in stat_result.all()}

        # Recent 24h
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_stmt = (
            select(func.count())
            .where(Alert.workspace_id == workspace_id)
            .where(Alert.created_at >= cutoff)
        )
        recent_24h = (await db.execute(recent_stmt)).scalar() or 0

        return {
            "total": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "recent_24h": recent_24h,
        }
