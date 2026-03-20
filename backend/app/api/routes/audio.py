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
from app.services.audio.stt import SpeechToTextService
from app.services.audio.vad import VoiceActivityDetector
from app.services.audio.separation import SourceSeparator
from app.services.audio.classification import AudioClassifier

router = APIRouter(prefix="/api/audio", tags=["audio"])

_augmenter = AudioAugmenter()
_stt = SpeechToTextService()
_vad = VoiceActivityDetector()
_separator = SourceSeparator()
_classifier = AudioClassifier()


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


# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(None),
):
    """Transcribe speech in an uploaded audio file using Whisper."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    result = await _stt.transcribe(audio, sr, language=language)
    return result


# ---------------------------------------------------------------------------
# Voice Activity Detection
# ---------------------------------------------------------------------------


@router.post("/vad")
async def vad(file: UploadFile = File(...)):
    """Detect speech segments in an uploaded audio file."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    segments = _vad.get_speech_segments(audio, sr)
    speech_ratio = _vad.get_speech_ratio(audio, sr)

    return {
        "segments": segments,
        "speech_ratio": round(speech_ratio, 4),
        "duration_s": round(len(audio) / sr, 4),
    }


# ---------------------------------------------------------------------------
# Source Separation
# ---------------------------------------------------------------------------


@router.post("/separate")
async def separate(
    file: UploadFile = File(...),
    stems: str = Form("vocals,drums,bass,other"),
):
    """Separate an audio file into stems, returned as base64-encoded WAV."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    stem_list = [s.strip() for s in stems.split(",") if s.strip()]
    separated = await _separator.separate(audio, sr, stems=stem_list)

    # Encode each stem as base64 WAV
    result: dict[str, str] = {}
    for name, stem_audio in separated.items():
        buf = io.BytesIO()
        sf.write(buf, stem_audio, sr, format="WAV")
        result[name] = base64.b64encode(buf.getvalue()).decode("ascii")

    return {"stems": result}


# ---------------------------------------------------------------------------
# Audio Classification
# ---------------------------------------------------------------------------


@router.post("/classify")
async def classify(file: UploadFile = File(...)):
    """Classify the content of an uploaded audio file."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    result = _classifier.classify_sound(audio, sr)
    return result
