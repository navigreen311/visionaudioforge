"""VAF v1 speaker-ID endpoints — voiceprint enrollment, verification,
continuous monitoring, and GDPR delete.

Mock decisions:
* enroll → always success, fixed quality scores [0.9, 0.92, 0.88]
* verify → match=True, confidence=0.92 by default
* ``?simulate=spoof`` → ``isLiveVoice=False`` (treated as failed verification)
* ``?simulate=mismatch`` → ``confidence=0.5``, ``match=False``
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from starlette.responses import Response

from app.api.deps.vaf_auth import require_vaf_bearer
from app.schemas.vaf_v1.speaker import (
    AntiSpoofResult,
    SpeakerContinuousRequest,
    VoiceprintEnrollment,
    VoiceprintVerification,
)
from app.schemas.vaf_v1.stt import StreamSessionResponse

router = APIRouter(prefix="/api/v1/speaker", tags=["VAF v1 / speaker"])


@router.post("/enroll", response_model=VoiceprintEnrollment)
async def enroll(
    userId: str = Form(...),
    sample_0: UploadFile = File(...),
    sample_1: UploadFile = File(...),
    sample_2: UploadFile = File(...),
    _: str = Depends(require_vaf_bearer),
) -> VoiceprintEnrollment:
    """Mock voiceprint enrollment — accepts userId + 3 audio samples."""
    # Drain uploads so the multipart parser sees them consumed.
    samples = [sample_0, sample_1, sample_2]
    for s in samples:
        await s.read()

    sample_urls: List[str] = [
        f"https://cdn.vaf.example/voiceprints/{userId}/sample_{i}.wav"
        for i in range(len(samples))
    ]

    return VoiceprintEnrollment(
        user_id=userId,
        sample_urls=sample_urls,
        quality_scores=[0.9, 0.92, 0.88],
        enrolled=True,
        enrolled_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/verify", response_model=VoiceprintVerification)
async def verify(
    userId: str = Form(...),
    audio: UploadFile = File(...),
    simulate: Optional[str] = Query(default=None),
    _: str = Depends(require_vaf_bearer),
) -> VoiceprintVerification:
    """Mock voiceprint verification with ``?simulate=spoof|mismatch`` variants."""
    start = time.perf_counter()
    await audio.read()
    latency_ms = (time.perf_counter() - start) * 1000.0

    if simulate == "spoof":
        return VoiceprintVerification(
            match=False,
            confidence=0.92,
            threshold=0.85,
            latency_ms=round(latency_ms, 2),
            anti_spoof_result=AntiSpoofResult(
                is_live_voice=False,
                is_not_synthesized=False,
                confidence=0.99,
            ),
        )

    if simulate == "mismatch":
        return VoiceprintVerification(
            match=False,
            confidence=0.5,
            threshold=0.85,
            latency_ms=round(latency_ms, 2),
            anti_spoof_result=AntiSpoofResult(
                is_live_voice=True,
                is_not_synthesized=True,
                confidence=0.99,
            ),
        )

    return VoiceprintVerification(
        match=True,
        confidence=0.92,
        threshold=0.85,
        latency_ms=round(latency_ms, 2),
        anti_spoof_result=AntiSpoofResult(
            is_live_voice=True,
            is_not_synthesized=True,
            confidence=0.99,
        ),
    )


@router.post("/continuous/create", response_model=StreamSessionResponse)
async def create_continuous(
    body: SpeakerContinuousRequest,
    _: str = Depends(require_vaf_bearer),
) -> StreamSessionResponse:
    """Allocate a continuous-verification session for a known user."""
    session_id = str(uuid.uuid4())
    return StreamSessionResponse(
        session_id=session_id,
        websocket_url=f"ws://localhost:4100/ws/speaker/{session_id}",
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voiceprint(
    user_id: str,
    _: str = Depends(require_vaf_bearer),
) -> Response:
    """GDPR-style hard delete of a user's voiceprint data."""
    # Mock: nothing to delete; the contract just needs to honor 204.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
