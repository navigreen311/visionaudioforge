"""Pydantic schemas for vision preprocessing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VisionOperation(BaseModel):
    op: str
    params: dict = Field(default_factory=dict)


class VisionAnalyzeResponse(BaseModel):
    image: str
    stats: dict
    operations_applied: list
    processing_time_ms: float


class ScreenAnalyzeResponse(BaseModel):
    brightness: float
    edge_density: float
    dominant_colors: list
    resolution: list
