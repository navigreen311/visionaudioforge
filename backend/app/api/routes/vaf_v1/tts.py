"""VAF v1 TTS endpoints — voices catalog + synthesis + streaming session.

The synthesize endpoint returns raw audio bytes (mock silent MP3) with
``X-Audio-Duration`` and ``X-Latency-Ms`` headers, matching what the PAF
client reads.
"""

from __future__ import annotations

import time
import uuid
from typing import List

from fastapi import APIRouter, Depends
from starlette.responses import Response

from app.api.deps.vaf_auth import require_vaf_bearer
from app.api.routes.vaf_v1.health import record_latency
from app.schemas.vaf_v1.stt import StreamSessionResponse
from app.schemas.vaf_v1.tts import TTSStreamCreateRequest, VAFSpeechRequest, VAFVoice

router = APIRouter(prefix="/api/v1/tts", tags=["VAF v1 / tts"])


# Static voice catalog (2 professional, 1 warm, 1 cloned).
_VOICES: List[VAFVoice] = [
    VAFVoice(
        id="vaf-pro-female-01",
        name="Ava — Professional",
        gender="female",
        language="en-US",
        accent="general-american",
        style="professional",
        preview_url="https://cdn.vaf.example/previews/ava-pro.mp3",
        is_cloned=False,
    ),
    VAFVoice(
        id="vaf-pro-male-01",
        name="Marcus — Professional",
        gender="male",
        language="en-US",
        accent="general-american",
        style="professional",
        preview_url="https://cdn.vaf.example/previews/marcus-pro.mp3",
        is_cloned=False,
    ),
    VAFVoice(
        id="vaf-warm-female-01",
        name="Iris — Warm",
        gender="female",
        language="en-US",
        accent="california",
        style="warm",
        preview_url="https://cdn.vaf.example/previews/iris-warm.mp3",
        is_cloned=False,
    ),
    VAFVoice(
        id="vaf-cloned-shadow-default",
        name="Shadow Default (Cloned)",
        gender="neutral",
        language="en-US",
        accent="general-american",
        style="confident",
        preview_url="https://cdn.vaf.example/previews/shadow-cloned.mp3",
        is_cloned=True,
    ),
]


# Minimal "silent" MP3 frame — a valid byte stream so the client can read it
# as audio. Real synthesis produces a proper encoded file.
_SILENT_MP3 = (
    b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


@router.get("/voices", response_model=List[VAFVoice])
async def get_voices(_: str = Depends(require_vaf_bearer)) -> List[VAFVoice]:
    """Return the catalog of available TTS voices."""
    return _VOICES


@router.post("/synthesize")
async def synthesize(
    body: VAFSpeechRequest,
    _: str = Depends(require_vaf_bearer),
) -> Response:
    """Mock speech synthesis — returns audio bytes + duration/latency headers."""
    start = time.perf_counter()

    # Mock duration ~ 60 ms / character, capped at 30s
    duration_s = min(30.0, max(0.5, len(body.text) * 0.06))
    latency_ms = (time.perf_counter() - start) * 1000.0
    record_latency("tts", latency_ms)

    media_type = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "pcm": "audio/L16",
    }.get(body.format.lower(), "audio/mpeg")

    return Response(
        content=_SILENT_MP3,
        media_type=media_type,
        headers={
            "X-Audio-Duration": f"{duration_s:.3f}",
            "X-Latency-Ms": f"{latency_ms:.2f}",
        },
    )


@router.post("/stream/create", response_model=StreamSessionResponse)
async def create_stream(
    body: TTSStreamCreateRequest,
    _: str = Depends(require_vaf_bearer),
) -> StreamSessionResponse:
    """Allocate a streaming TTS session and return its WebSocket URL."""
    session_id = str(uuid.uuid4())
    return StreamSessionResponse(
        session_id=session_id,
        websocket_url=f"ws://localhost:4100/ws/tts/{session_id}",
    )
