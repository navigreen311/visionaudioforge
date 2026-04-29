"""VAF v1 audio-quality endpoint — mock noise/echo/SNR report.

``?simulate=poor`` flips the report into a "switch_to_text" recommendation
with high noise, exercising the PAF fallback path that bypasses STT and
asks the user to type instead.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.deps.vaf_auth import require_vaf_bearer
from app.schemas.vaf_v1.audio import AudioQualityReport

router = APIRouter(prefix="/api/v1/audio", tags=["VAF v1 / audio"])


@router.post("/quality", response_model=AudioQualityReport)
async def quality(
    audio: UploadFile = File(...),
    enhance: Optional[bool] = Form(default=False),
    denoise: Optional[bool] = Form(default=False),
    removeEcho: Optional[bool] = Form(default=False),
    simulate: Optional[str] = Query(default=None),
    _: str = Depends(require_vaf_bearer),
) -> AudioQualityReport:
    """Mock audio-quality analysis with ``?simulate=poor`` variant."""
    # Drain the upload to confirm multipart parsing succeeded.
    await audio.read()

    if simulate == "poor":
        return AudioQualityReport(
            noise_level=0.85,
            echo_detected=True,
            clipping_detected=True,
            signal_to_noise=6.0,
            packet_loss=0.12,
            bandwidth="narrowband",
            recommendation="switch_to_text",
        )

    return AudioQualityReport(
        noise_level=0.2,
        echo_detected=False,
        clipping_detected=False,
        signal_to_noise=28.0,
        packet_loss=0.0,
        bandwidth="wideband",
        recommendation="good",
    )
