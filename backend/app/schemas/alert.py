"""Pydantic schemas for the Alert system."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Sub-schemas
# ------------------------------------------------------------------


class ConditionSchema(BaseModel):
    """Condition configuration for an alert rule."""

    type: Literal["threshold", "compound", "temporal"] = "threshold"
    metric: str
    operator: Literal[">", "<", "==", "!="]
    value: float
    window_seconds: Optional[int] = None


class ActionSchema(BaseModel):
    """Action configuration for an alert rule."""

    type: Literal["webhook", "email", "slack", "log"]
    config: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Alert Rule schemas
# ------------------------------------------------------------------


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool = True


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


class AlertAction(BaseModel):
    action: str
    status: Literal["sent", "failed"]
    error: Optional[str] = None
