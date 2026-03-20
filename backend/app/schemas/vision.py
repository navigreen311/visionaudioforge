"""Schemas for vision motion analysis endpoints."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class OpticalFlowMethod(str, Enum):
    LUCAS_KANADE = "lucas-kanade"
    FARNEBACK = "farneback"


class FrameDiffMethod(str, Enum):
    CONSECUTIVE = "consecutive"
    THREE_FRAME = "three-frame"


class MotionStats(BaseModel):
    mean_magnitude: float = 0.0
    max_magnitude: float = 0.0
    motion_area_pct: float = 0.0
    dominant_direction_deg: float = 0.0


class OpticalFlowResponse(BaseModel):
    method: str
    stats: MotionStats
    visualization: str = Field(description="Base64-encoded visualization image")
    processing_time_ms: float


class FrameDiffResponse(BaseModel):
    method: str
    motion_percentage: float
    motion_mask: str = Field(description="Base64-encoded motion mask image")
    stats: MotionStats
    processing_time_ms: float
