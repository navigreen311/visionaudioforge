from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    agent_type: str
    config: Optional[dict[str, Any]] = None


class AgentRead(BaseModel):
    id: UUID
    name: str
    agent_type: str
    config: dict[str, Any]
    status: str
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentMemoryRead(BaseModel):
    id: UUID
    agent_id: UUID
    content: str
    importance_score: float
    freshness_score: float
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: str
    content: str
