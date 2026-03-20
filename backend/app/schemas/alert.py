from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    name: str
    conditions: dict[str, Any]
    actions: dict[str, Any]
    enabled: bool = True


class AlertRuleRead(BaseModel):
    id: UUID
    name: str
    conditions: dict[str, Any]
    actions: dict[str, Any]
    enabled: bool
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
