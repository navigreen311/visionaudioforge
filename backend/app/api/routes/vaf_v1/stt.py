"""VAF v1 STT endpoints — mock transcription + streaming session creation.

Returns spec-shaped fixture data; real Whisper/streaming backends slot in
later behind these handlers.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps.vaf_auth import require_vaf_bearer
from app.api.routes.vaf_v1.health import record_latency
from app.schemas.vaf_v1.stt import (
    STTStreamCreateRequest,
    StreamSessionResponse,
    VAFTranscriptionResult,
    WordTiming,
)

router = APIRouter(prefix="/api/v1/stt", tags=["VAF v1 / stt"])


@router.post("/transcribe", response_model=VAFTranscriptionResult)
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("en-US"),
    model: str = Form("accurate"),
    vocabulary: Optional[str] = Form(None),
    _: str = Depends(require_vaf_bearer),
) -> VAFTranscriptionResult:
    """Mock batch transcription matching ``VAFTranscriptionResult``."""
    start = time.perf_counter()
    # Read but don't process — proves multipart wiring works without
    # imposing real audio-decoding cost on the mock.
    await audio.read()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    record_latency("stt", elapsed_ms)

    return VAFTranscriptionResult(
        text="[mock transcription]",
        confidence=0.95,
        is_final=True,
        words=[
            WordTiming(word="[mock", start=0.0, end=0.3, confidence=0.95),
            WordTiming(word="transcription]", start=0.3, end=0.9, confidence=0.95),
        ],
        language=language,
        latency_ms=round(elapsed_ms, 2),
    )


@router.post("/stream/create", response_model=StreamSessionResponse)
async def create_stream(
    body: STTStreamCreateRequest,
    _: str = Depends(require_vaf_bearer),
) -> StreamSessionResponse:
    """Allocate a streaming STT session and return its WebSocket URL."""
    session_id = str(uuid.uuid4())
    return StreamSessionResponse(
        session_id=session_id,
        websocket_url=f"ws://localhost:4100/ws/stt/{session_id}",
    )
