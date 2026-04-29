"""VAF v1 — Sentiment endpoints.

Mock-but-correct implementations of the sentiment intelligence routes
documented in the PAF integration spec. Real models slot in behind
these handlers later; the response contracts are frozen now so the PAF
client (Shadow) can be built against them in parallel.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.schemas.vaf_v1.sentiment import (
    EmotionScores,
    SentimentAnalyzeRequest,
    SentimentAnalyzeResponse,
    SentimentPeak,
    SentimentResult,
    SentimentStreamCreateRequest,
    SentimentStreamCreateResponse,
    SentimentTimelinePoint,
)

from ._auth_shim import vaf_auth

router = APIRouter(prefix="/api/v1/sentiment", tags=["vaf-v1-sentiment"])


def _neutral_result(satisfaction: float = 0.7) -> SentimentResult:
    """Build a plausible 'neutral' sentiment fixture."""
    return SentimentResult(
        overall="neutral",
        confidence=0.88,
        emotions=EmotionScores(
            anger=0.05,
            frustration=0.10,
            anxiety=0.08,
            satisfaction=satisfaction,
            confusion=0.07,
            urgency=0.12,
        ),
        riskFlags=[],
        suggestedAction="continue",
    )


@router.post(
    "/stream/create",
    response_model=SentimentStreamCreateResponse,
    status_code=status.HTTP_200_OK,
)
async def create_sentiment_stream(
    body: SentimentStreamCreateRequest,
    _token: str = Depends(vaf_auth),
) -> SentimentStreamCreateResponse:
    """Open a streaming sentiment session for an in-progress call."""
    session_id = f"sent_{uuid.uuid4().hex[:16]}"
    return SentimentStreamCreateResponse(
        sessionId=session_id,
        websocketUrl=f"wss://vaf.local/ws/sentiment/{session_id}",
    )


@router.post("/analyze", response_model=SentimentAnalyzeResponse)
async def analyze_recording(
    body: SentimentAnalyzeRequest,
    _token: str = Depends(vaf_auth),
) -> SentimentAnalyzeResponse:
    """Batch-analyse a completed call recording.

    Mock returns three timeline points spread across 0-30s with an overall
    'neutral' result and one satisfaction peak — enough fixture data for
    the PAF client to render the timeline UI.
    """
    timeline = [
        SentimentTimelinePoint(timestamp=0.0, sentiment=_neutral_result(0.65)),
        SentimentTimelinePoint(timestamp=15.0, sentiment=_neutral_result(0.72)),
        SentimentTimelinePoint(timestamp=30.0, sentiment=_neutral_result(0.78)),
    ]
    overall = _neutral_result(0.7)
    peaks = [SentimentPeak(timestamp=15.0, event="satisfaction_peak")]
    return SentimentAnalyzeResponse(timeline=timeline, overall=overall, peaks=peaks)
