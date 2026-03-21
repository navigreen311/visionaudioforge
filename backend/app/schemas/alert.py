"""Pydantic schemas for the Alert system."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Sub-schemas
# ------------------------------------------------------------------


class ConditionSchema(BaseModel):
    """Condition configuration for an alert rule.

    Supports threshold, compound, temporal, and cross_modal types.
    """

    type: Literal["threshold", "compound", "temporal", "cross_modal"] = "threshold"
    # Threshold fields
    metric: Optional[str] = None
    operator: Optional[Literal[">", "<", "==", "!=", ">=", "<="]] = None
    value: Optional[float] = None
    window_seconds: Optional[int] = None
    # Compound fields
    conditions: Optional[list[dict[str, Any]]] = None  # sub-conditions for AND/OR
    # Temporal fields
    condition: Optional[dict[str, Any]] = None  # base condition
    min_occurrences: Optional[int] = None
    # Cross-modal fields
    vision_condition: Optional[dict[str, Any]] = None
    audio_condition: Optional[dict[str, Any]] = None
    require_both: Optional[bool] = None


class ActionSchema(BaseModel):
    """Action configuration for an alert rule."""

    type: Literal["webhook", "email", "slack", "discord", "sms", "log"]
    config: dict[str, Any] = Field(default_factory=dict)


class EscalationLevelSchema(BaseModel):
    """A single escalation level configuration."""

    after_minutes: int = Field(..., gt=0)
    action: str


class EscalationConfigSchema(BaseModel):
    """Full escalation policy configuration."""

    levels: list[EscalationLevelSchema] = Field(default_factory=list)


# ------------------------------------------------------------------
# Alert Rule schemas
# ------------------------------------------------------------------


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool = True
    escalation_config: Optional[dict[str, Any]] = None


class AlertRuleRead(BaseModel):
    id: UUID
    name: str
    conditions: dict[str, Any]
    actions: list[dict[str, Any]] | dict[str, Any]
    enabled: bool
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    conditions: Optional[dict[str, Any]] = None
    actions: Optional[list[dict[str, Any]]] = None
    enabled: Optional[bool] = None
    escalation_config: Optional[dict[str, Any]] = None


# ------------------------------------------------------------------
# Alert schemas
# ------------------------------------------------------------------


class AlertRead(BaseModel):
    id: UUID
    rule_id: UUID
    severity: str
    payload: Optional[dict[str, Any]] = None
    status: str
    acknowledged_by: Optional[UUID] = None
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertStats(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    recent_24h: int
    critical_24h: int = 0
    acknowledged: int = 0
    unresolved: int = 0
    recent: list[dict[str, Any]] = []


class AlertStatsSummary(BaseModel):
    """Compact 4-card summary for the alerts dashboard."""

    critical: int = 0
    critical_trend: int = 0
    warning: int = 0
    warning_trend: int = 0
    info: int = 0
    info_trend: int = 0
    acknowledged_today: int = 0
    acknowledged_today_trend: int = 0


class AlertStatusUpdate(BaseModel):
    """Body for PATCH /api/alerts/{id}."""

    status: str


class AlertAction(BaseModel):
    action: str
    status: Literal["sent", "failed"]
    error: Optional[str] = None


# ------------------------------------------------------------------
# Test / delivery schemas
# ------------------------------------------------------------------


class RuleTestRequest(BaseModel):
    """Request body for testing a rule against sample metrics."""

    conditions: dict[str, Any]
    sample_metrics: dict[str, float]


class RuleTestResponse(BaseModel):
    """Result of testing a rule."""

    triggered: bool
    matched_conditions: list[str]
    details: str


class DeliveryTestRequest(BaseModel):
    """Request body for testing a delivery channel."""

    channel: Literal["webhook", "email", "slack", "discord", "sms"]
    config: dict[str, Any]


class DeliveryTestResponse(BaseModel):
    """Result of testing a delivery channel."""

    status: str
    note: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None


class EscalateRequest(BaseModel):
    """Request body for manually escalating an alert."""

    escalation_config: dict[str, Any]
