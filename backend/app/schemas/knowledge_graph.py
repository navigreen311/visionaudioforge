"""Pydantic schemas for the Knowledge Graph system."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Node schemas
# ------------------------------------------------------------------


class GraphNodeCreate(BaseModel):
    node_type: str = Field(..., max_length=50, description="person/object/location/event/vehicle")
    label: str = Field(..., max_length=200)
    properties: dict[str, Any] = Field(default_factory=dict)
    workspace_id: UUID


class GraphNodeRead(BaseModel):
    id: UUID
    node_type: str
    label: str
    properties: dict[str, Any]
    workspace_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Edge schemas
# ------------------------------------------------------------------


class GraphEdgeCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    edge_type: str = Field(..., max_length=100)
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    workspace_id: Optional[UUID] = None


class GraphEdgeRead(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    edge_type: str
    properties: dict[str, Any]
    confidence: float
    workspace_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Scene extraction
# ------------------------------------------------------------------


class DetectionInput(BaseModel):
    class_name: str
    bbox: dict[str, float] = Field(..., description="Bounding box {x, y, w, h}")
    confidence: float = 0.0


class SceneExtractRequest(BaseModel):
    detections: list[DetectionInput]


class SceneGraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


# ------------------------------------------------------------------
# Event linking
# ------------------------------------------------------------------


class EventLinkRequest(BaseModel):
    event_ids: list[UUID]
    time_window: float = Field(default=30.0, description="Time window in seconds")


# ------------------------------------------------------------------
# Analytics
# ------------------------------------------------------------------


class CentralityItem(BaseModel):
    node_id: str
    label: str
    score: float


class CommunityItem(BaseModel):
    community_id: int
    nodes: list[dict[str, Any]]


class AnomalyItem(BaseModel):
    node_id: str
    anomaly_score: float
    reason: str
