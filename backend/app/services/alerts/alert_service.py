"""AlertService — CRUD for alert rules and incident lifecycle management.

Includes compound/temporal/cross-modal rule evaluation, deduplication,
auto-severity scoring, and escalation policies.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertRule, AlertSeverity, AlertStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class UnknownActorError(ValueError):
    """Raised when the user acknowledging or resolving an alert does not exist.

    `alerts.acknowledged_by` is a foreign key to `users`, so an unknown id used
    to surface as an unhandled IntegrityError — a 500 with a traceback rather
    than a message telling the caller which value was wrong.
    """


# Severity levels ordered for escalation
_SEVERITY_ORDER = [
    AlertSeverity.low,
    AlertSeverity.medium,
    AlertSeverity.high,
    AlertSeverity.critical,
]


# ======================================================================
# RuleEvaluationEngine — compound / temporal / cross-modal evaluation
# ======================================================================


class RuleEvaluationEngine:
    """Stateful engine that evaluates compound, temporal, and cross-modal rules.

    Keeps an in-memory event history for temporal rule tracking.
    """

    def __init__(self) -> None:
        # event_history: key = (rule_id or condition hash) -> list of timestamps
        self._event_history: dict[str, list[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        rule: dict[str, Any],
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Evaluate a rule against current metrics.

        Args:
            rule: The condition dict (may be nested).
            metrics: Current metric name -> value mapping.

        Returns:
            {"triggered": bool, "matched_conditions": list, "details": str}
        """
        matched: list[str] = []
        triggered = self._dispatch(rule, metrics, matched)
        details = "; ".join(matched) if matched else "No conditions matched"
        return {
            "triggered": triggered,
            "matched_conditions": matched,
            "details": details,
        }

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch(
        self,
        condition: dict[str, Any],
        metrics: dict[str, float],
        matched: list[str],
    ) -> bool:
        ctype = condition.get("type", "threshold")
        if ctype == "compound":
            return self._evaluate_compound(condition, metrics, matched)
        if ctype == "temporal":
            return self._evaluate_temporal(condition, metrics, matched)
        if ctype == "cross_modal":
            return self._evaluate_cross_modal(condition, metrics, matched)
        # Default: threshold
        metric_name = condition.get("metric", "")
        value = metrics.get(metric_name)
        if value is None:
            return False
        hit = self._evaluate_threshold(condition, value)
        if hit:
            matched.append(
                f"{metric_name} {condition.get('operator', '==')} {condition.get('value', 0)} (actual={value})"
            )
        return hit

    # ------------------------------------------------------------------
    # Threshold
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_threshold(condition: dict[str, Any], value: float) -> bool:
        """Evaluate a simple threshold condition."""
        operator = condition.get("operator", "==")
        threshold = float(condition.get("value", 0))
        if operator == ">":
            return value > threshold
        if operator == "<":
            return value < threshold
        if operator == "==":
            return value == threshold
        if operator == "!=":
            return value != threshold
        if operator == ">=":
            return value >= threshold
        if operator == "<=":
            return value <= threshold
        return False

    # ------------------------------------------------------------------
    # Compound (AND / OR with recursive sub-conditions)
    # ------------------------------------------------------------------

    def _evaluate_compound(
        self,
        condition: dict[str, Any],
        metrics: dict[str, float],
        matched: list[str],
    ) -> bool:
        """Evaluate compound AND/OR conditions recursively."""
        operator = condition.get("operator", "AND").upper()
        sub_conditions = condition.get("conditions", [])
        if not sub_conditions:
            return False

        if operator == "AND":
            all_matched = True
            for sub in sub_conditions:
                if not self._dispatch(sub, metrics, matched):
                    all_matched = False
            return all_matched
        else:  # OR
            any_matched = False
            for sub in sub_conditions:
                if self._dispatch(sub, metrics, matched):
                    any_matched = True
            return any_matched

    # ------------------------------------------------------------------
    # Temporal (N occurrences within a time window)
    # ------------------------------------------------------------------

    def _evaluate_temporal(
        self,
        condition: dict[str, Any],
        metrics: dict[str, float],
        matched: list[str],
    ) -> bool:
        """Track occurrences in a time window. Trigger only if threshold met."""
        base_condition = condition.get("condition", {})
        window_seconds = int(condition.get("window_seconds", 60))
        min_occurrences = int(condition.get("min_occurrences", 1))

        # Check if the base condition fires right now
        sub_matched: list[str] = []
        fires_now = self._dispatch(base_condition, metrics, sub_matched)

        # Build a stable key for the history
        history_key = f"temporal:{base_condition.get('metric', '')}:{base_condition.get('operator', '')}:{base_condition.get('value', '')}"
        now = time.time()

        if fires_now:
            self._event_history[history_key].append(now)

        # Prune events outside the window
        cutoff = now - window_seconds
        self._event_history[history_key] = [
            t for t in self._event_history[history_key] if t >= cutoff
        ]

        count = len(self._event_history[history_key])
        triggered = count >= min_occurrences
        if triggered:
            matched.extend(sub_matched)
            matched.append(
                f"temporal: {count}/{min_occurrences} occurrences in {window_seconds}s"
            )
        return triggered

    def _evaluate_temporal_with_history(
        self,
        condition: dict[str, Any],
        value: float,
        event_history: list[float],
    ) -> bool:
        """Evaluate temporal condition against an externally provided event history.

        Useful for testing or when history is stored externally.
        """
        base_condition = condition.get("condition", {})
        window_seconds = int(condition.get("window_seconds", 60))
        min_occurrences = int(condition.get("min_occurrences", 1))

        fires_now = self._evaluate_threshold(base_condition, value)
        now = time.time()
        if fires_now:
            event_history.append(now)

        cutoff = now - window_seconds
        recent = [t for t in event_history if t >= cutoff]
        return len(recent) >= min_occurrences

    # ------------------------------------------------------------------
    # Cross-modal (vision + audio)
    # ------------------------------------------------------------------

    def _evaluate_cross_modal(
        self,
        condition: dict[str, Any],
        metrics: dict[str, float],
        matched: list[str],
    ) -> bool:
        """Evaluate cross-modal conditions (vision + audio)."""
        vision_condition = condition.get("vision_condition", {})
        audio_condition = condition.get("audio_condition", {})
        require_both = condition.get("require_both", True)

        vision_matched: list[str] = []
        audio_matched: list[str] = []
        vision_hit = self._dispatch(vision_condition, metrics, vision_matched)
        audio_hit = self._dispatch(audio_condition, metrics, audio_matched)

        if require_both:
            triggered = vision_hit and audio_hit
        else:
            triggered = vision_hit or audio_hit

        if triggered:
            if vision_hit:
                matched.extend(vision_matched)
            if audio_hit:
                matched.extend(audio_matched)
            matched.append(
                f"cross_modal: vision={'hit' if vision_hit else 'miss'}, "
                f"audio={'hit' if audio_hit else 'miss'}, "
                f"mode={'AND' if require_both else 'OR'}"
            )
        return triggered


# Singleton engine instance
_engine = RuleEvaluationEngine()


def get_rule_engine() -> RuleEvaluationEngine:
    """Return the shared RuleEvaluationEngine singleton."""
    return _engine


# ======================================================================
# Deduplication & auto-severity
# ======================================================================


async def deduplicate_alert(
    db: AsyncSession,
    new_alert_rule_id: UUID,
    new_alert_severity: AlertSeverity | str,
    workspace_id: UUID,
    window_minutes: int = 5,
) -> Alert | None:
    """Check for an existing identical alert within the dedup window.

    If found, increments a `duplicate_count` in the payload and returns
    the existing alert. Returns None if no duplicate exists.
    """
    if isinstance(new_alert_severity, str):
        new_alert_severity = AlertSeverity(new_alert_severity)

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    stmt = (
        select(Alert)
        .where(
            Alert.rule_id == new_alert_rule_id,
            Alert.severity == new_alert_severity,
            Alert.workspace_id == workspace_id,
            Alert.created_at >= cutoff,
            Alert.status.in_([AlertStatus.new, AlertStatus.acknowledged]),
        )
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is None:
        return None

    # Increment duplicate count in payload
    payload = dict(existing.payload or {})
    payload["duplicate_count"] = payload.get("duplicate_count", 1) + 1
    existing.payload = payload
    await db.commit()
    await db.refresh(existing)
    logger.info(
        "Deduplicated alert for rule %s — count now %d",
        new_alert_rule_id,
        payload["duplicate_count"],
    )
    return existing


def auto_severity_scoring(
    conditions_met: int,
    base_severity: AlertSeverity | str,
) -> AlertSeverity:
    """Escalate severity when multiple conditions are triggered.

    1 condition  -> base_severity
    2+ conditions -> one level up (capped at critical)
    """
    if isinstance(base_severity, str):
        base_severity = AlertSeverity(base_severity)

    if conditions_met <= 1:
        return base_severity

    idx = _SEVERITY_ORDER.index(base_severity)
    escalated_idx = min(idx + 1, len(_SEVERITY_ORDER) - 1)
    return _SEVERITY_ORDER[escalated_idx]


# ======================================================================
# EscalationPolicy
# ======================================================================


class EscalationPolicy:
    """Manages time-based alert escalation."""

    @staticmethod
    async def escalate(
        db: AsyncSession,
        alert_id: UUID,
        escalation_config: dict[str, Any],
    ) -> Alert:
        """Apply the next escalation level to an alert.

        escalation_config example:
        {
            "levels": [
                {"after_minutes": 5, "action": "notify_team_lead"},
                {"after_minutes": 15, "action": "notify_manager"},
                {"after_minutes": 30, "action": "page_oncall"},
            ]
        }
        """
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert is None:
            raise ValueError(f"Alert {alert_id} not found")

        payload = dict(alert.payload or {})
        current_level = payload.get("escalation_level", -1)
        levels = escalation_config.get("levels", [])
        next_level = current_level + 1

        if next_level >= len(levels):
            logger.info("Alert %s already at max escalation level", alert_id)
            return alert

        level_config = levels[next_level]
        payload["escalation_level"] = next_level
        payload["escalation_action"] = level_config.get("action", "unknown")
        payload["escalated_at"] = datetime.now(timezone.utc).isoformat()
        alert.payload = payload

        # Bump severity on escalation
        if next_level >= 2:
            alert.severity = AlertSeverity.critical
        elif next_level >= 1:
            current_sev = alert.severity if isinstance(alert.severity, AlertSeverity) else AlertSeverity(alert.severity)
            alert.severity = auto_severity_scoring(2, current_sev)

        await db.commit()
        await db.refresh(alert)
        logger.info(
            "Escalated alert %s to level %d (action=%s)",
            alert_id,
            next_level,
            level_config.get("action"),
        )
        return alert

    @staticmethod
    async def check_escalations(
        db: AsyncSession,
        workspace_id: UUID,
        escalation_config: dict[str, Any] | None = None,
    ) -> list[Alert]:
        """Find alerts that need escalation (unacknowledged past their timer).

        Returns alerts in 'new' status older than the smallest escalation
        window that haven't been escalated to that level yet.
        """
        if not escalation_config:
            escalation_config = {
                "levels": [
                    {"after_minutes": 5, "action": "notify_team_lead"},
                    {"after_minutes": 15, "action": "notify_manager"},
                    {"after_minutes": 30, "action": "page_oncall"},
                ]
            }

        levels = escalation_config.get("levels", [])
        if not levels:
            return []

        # Find the smallest window
        min_minutes = min(lvl.get("after_minutes", 5) for lvl in levels)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=min_minutes)

        stmt = (
            select(Alert)
            .where(
                Alert.workspace_id == workspace_id,
                Alert.status == AlertStatus.new,
                Alert.created_at <= cutoff,
            )
            .order_by(Alert.created_at.asc())
        )
        result = await db.execute(stmt)
        candidates = list(result.scalars().all())

        # Filter: only those that haven't reached their current escalation tier
        needs_escalation = []
        for alert in candidates:
            payload = alert.payload or {}
            current_level = payload.get("escalation_level", -1)
            age_minutes = (
                datetime.now(timezone.utc) - alert.created_at
            ).total_seconds() / 60.0

            # Check if there's a next level the alert qualifies for
            for i, level in enumerate(levels):
                if i > current_level and age_minutes >= level.get("after_minutes", 0):
                    needs_escalation.append(alert)
                    break

        return needs_escalation


# ======================================================================
# AlertService
# ======================================================================


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
    # Rule evaluation (enhanced with compound/temporal/cross-modal)
    # ------------------------------------------------------------------

    @staticmethod
    async def evaluate_rule(
        db: AsyncSession,
        rule: AlertRule,
        metric_value: float,
        metrics: dict[str, float] | None = None,
    ) -> Optional[Alert]:
        """Evaluate a rule against metric(s). Create an Alert if triggered.

        Supports condition types: threshold, compound, temporal, cross_modal.
        """
        conditions = rule.conditions
        ctype = conditions.get("type", "threshold")

        # Build metrics dict — use explicit metrics if provided, else infer
        if metrics is None:
            metric_name = conditions.get("metric", "unknown")
            metrics = {metric_name: metric_value}

        engine = get_rule_engine()

        if ctype in ("compound", "temporal", "cross_modal"):
            result = engine.evaluate(conditions, metrics)
            if not result["triggered"]:
                return None
            num_matched = len(result["matched_conditions"])
            base_severity = AlertSeverity.medium
            severity = auto_severity_scoring(num_matched, base_severity)
            payload = {
                "metric": conditions.get("metric", "compound"),
                "metrics": metrics,
                "matched_conditions": result["matched_conditions"],
                "details": result["details"],
                "rule_name": rule.name,
            }
        else:
            # Simple threshold
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

            # Determine severity
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

        # Deduplicate before creating
        existing = await deduplicate_alert(
            db,
            new_alert_rule_id=rule.id,
            new_alert_severity=severity,
            workspace_id=rule.workspace_id,
        )
        if existing is not None:
            return existing

        alert = await AlertService.trigger_alert(
            db,
            rule_id=rule.id,
            severity=severity,
            payload=payload,
            workspace_id=rule.workspace_id,
        )
        return alert

    @staticmethod
    async def test_rule(
        rule_conditions: dict[str, Any],
        sample_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Test a rule against sample metrics without persisting anything."""
        engine = get_rule_engine()
        return engine.evaluate(rule_conditions, sample_metrics)

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

        # The console's notification bell used to show five hardcoded entries,
        # one of which read "Critical alert triggered". This is where that
        # sentence becomes true. `emit` never raises: the alert is already
        # committed and a failed notification must not undo it.
        from app.models.notification import NotificationType
        from app.services.notifications.service import NotificationService

        await NotificationService.emit(
            db,
            workspace_id,
            NotificationType.alert,
            title=f"{severity.value.title()} alert triggered",
            description=str(payload.get("message") or payload.get("summary") or "")[:500],
            action_url="/alerts",
        )

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
        if await db.get(User, user_id) is None:
            raise UnknownActorError(f"User {user_id} does not exist")
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
