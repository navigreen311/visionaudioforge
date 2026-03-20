"""Audio API routes — analysis and augmentation endpoints."""

from __future__ import annotations

import base64
import io
import json
import time

import librosa
import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.responses import JSONResponse

from app.schemas.audio import AudioAugmentResponse
from app.services.audio.augmentation import AudioAugmenter
from app.services.audio.augmentation_presets import PRESETS

router = APIRouter(prefix="/api/audio", tags=["audio"])

_augmenter = AudioAugmenter()


@router.post("/analyze")
async def analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "audio"})


@router.post("/augment", response_model=AudioAugmentResponse)
async def augment(
    file: UploadFile = File(...),
    config: str = Form(...),
):
    """Augment an uploaded audio file.

    *config* can be either:
    - A preset name (e.g. ``"speech_robust"``).
    - A JSON array of augmentation step objects.
    """
    start = time.perf_counter()

    # --- Load audio -------------------------------------------------------
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    original_duration_s = len(audio) / sr

    # --- Resolve pipeline config ------------------------------------------
    pipeline: list[dict]
    config_stripped = config.strip()

    if config_stripped in PRESETS:
        pipeline = PRESETS[config_stripped]
    else:
        try:
            parsed = json.loads(config_stripped)
            if not isinstance(parsed, list):
                raise ValueError("Config must be a JSON array of augmentation steps")
            pipeline = parsed
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid config — expected a preset name or JSON array: {exc}",
            )

    # --- Apply augmentation -----------------------------------------------
    augmented_audio, applied = _augmenter.apply_pipeline(audio, sr, pipeline)

    augmented_duration_s = len(augmented_audio) / sr

    # --- Encode result as base64 WAV --------------------------------------
    buf = io.BytesIO()
    sf.write(buf, augmented_audio, sr, format="WAV")
    augmented_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return AudioAugmentResponse(
        augmented_audio=augmented_b64,
        applied_augmentations=applied,
        original_duration_s=round(original_duration_s, 4),
        augmented_duration_s=round(augmented_duration_s, 4),
        processing_time_ms=round(elapsed_ms, 2),
    )
