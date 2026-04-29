"""Schemas for /api/v1/sentiment/*.

Mirrors the SentimentResult shape from the PAF VAF integration spec. Field
names are intentionally camelCase to match the cross-service contract.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SentimentLabel = Literal["positive", "neutral", "negative", "hostile"]


class EmotionScores(BaseModel):
    """Per-emotion scalar scores in [0.0, 1.0]."""

    anger: float = Field(..., ge=0.0, le=1.0)
    frustration: float = Field(..., ge=0.0, le=1.0)
    anxiety: float = Field(..., ge=0.0, le=1.0)
    satisfaction: float = Field(..., ge=0.0, le=1.0)
    confusion: float = Field(..., ge=0.0, le=1.0)
    urgency: float = Field(..., ge=0.0, le=1.0)


class SentimentResult(BaseModel):
    """Single-point sentiment reading. Matches PAF spec exactly."""

    overall: SentimentLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    emotions: EmotionScores
    riskFlags: list[str] = Field(default_factory=list)
    suggestedAction: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# /sentiment/stream/create
# ---------------------------------------------------------------------------


class SentimentStreamCreateRequest(BaseModel):
    callId: str
    analyzeInterval: int = Field(5, ge=1, le=60, description="Seconds between analyses")
    includeSuggestions: bool = True
    alertOnHostile: bool = True


class SentimentStreamCreateResponse(BaseModel):
    sessionId: str
    websocketUrl: str


# ---------------------------------------------------------------------------
# /sentiment/analyze
# ---------------------------------------------------------------------------


class SentimentAnalyzeRequest(BaseModel):
    audioUrl: str


class SentimentTimelinePoint(BaseModel):
    timestamp: float
    sentiment: SentimentResult


class SentimentPeak(BaseModel):
    timestamp: float
    event: str


class SentimentAnalyzeResponse(BaseModel):
    timeline: list[SentimentTimelinePoint]
    overall: SentimentResult
    peaks: list[SentimentPeak]
