"""VAF v1 — Meeting intelligence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.vaf_v1.meeting import (
    ActionItem,
    Decision,
    MeetingProcessRequest,
    MeetingSegment,
    MeetingTranscript,
)

from ._auth_shim import vaf_auth

router = APIRouter(prefix="/api/v1/meeting", tags=["vaf-v1-meeting"])


@router.post("/process", response_model=MeetingTranscript)
async def process_meeting(
    body: MeetingProcessRequest,
    _token: str = Depends(vaf_auth),
) -> MeetingTranscript:
    """Process a meeting recording into a structured transcript.

    Mock returns 3 segments alternating between 2 speakers, two action
    items, one decision, and a single-paragraph summary. The real model
    will replace the body of this handler.
    """
    segments = [
        MeetingSegment(
            speaker="Alice",
            speakerId="spk_alice",
            text="Thanks for joining. Let's review the compliance package timeline.",
            startTime=0.0,
            endTime=6.5,
            confidence=0.96,
        ),
        MeetingSegment(
            speaker="Bob",
            speakerId="spk_bob",
            text="I can have the updated package over to you by Friday.",
            startTime=6.6,
            endTime=11.2,
            confidence=0.94,
        ),
        MeetingSegment(
            speaker="Alice",
            speakerId="spk_alice",
            text="Great. I'll review and respond by Tuesday — that's our decision.",
            startTime=11.3,
            endTime=17.0,
            confidence=0.95,
        ),
    ]

    action_items = [
        ActionItem(
            description="Send updated compliance package",
            assignee="Bob",
            deadline="2026-05-01",
            priority="high",
        ),
        ActionItem(
            description="Review compliance package and respond",
            assignee="Alice",
            deadline="2026-05-05",
            priority="medium",
        ),
    ] if body.extractActionItems else []

    decisions = [
        Decision(
            decision="Bob delivers compliance package by Friday; Alice responds by Tuesday",
            madeBy="Alice",
            context="Quarterly compliance review meeting",
        ),
    ] if body.extractDecisions else []

    summary = (
        "Alice and Bob aligned on the compliance package deliverable. "
        "Bob will send the updated package by Friday, and Alice will "
        "review and respond by Tuesday."
    ) if body.generateSummary else ""

    return MeetingTranscript(
        segments=segments,
        summary=summary,
        actionItems=action_items,
        decisions=decisions,
        keyTopics=["compliance", "timeline", "deliverables"],
        duration=17.0,
        speakerCount=2,
    )
