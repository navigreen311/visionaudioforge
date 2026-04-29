"""Schemas for /api/v1/meeting/*.

Mirrors the MeetingTranscript shape from the PAF VAF integration spec.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class KnownSpeaker(BaseModel):
    name: str
    voiceprintId: str


class MeetingProcessRequest(BaseModel):
    audioUrl: str
    knownSpeakers: Optional[list[KnownSpeaker]] = None
    extractActionItems: bool = True
    extractDecisions: bool = True
    generateSummary: bool = True


class MeetingSegment(BaseModel):
    speaker: str
    speakerId: str
    text: str
    startTime: float
    endTime: float
    confidence: float = Field(..., ge=0.0, le=1.0)


class ActionItem(BaseModel):
    description: str
    assignee: str
    deadline: Optional[str] = None
    priority: Literal["high", "medium", "low"]


class Decision(BaseModel):
    decision: str
    madeBy: str
    context: str


class MeetingTranscript(BaseModel):
    """Full transcript + extracted intelligence. Matches PAF spec."""

    segments: list[MeetingSegment]
    summary: str
    actionItems: list[ActionItem]
    decisions: list[Decision]
    keyTopics: list[str]
    duration: float
    speakerCount: int
