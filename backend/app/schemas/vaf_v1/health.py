"""Health-endpoint schema for VAF v1 (PAF integration)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VAFLatencies(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stt: float
    tts: float
    sentiment: float


class VAFHealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    latencies: VAFLatencies
    version: str
