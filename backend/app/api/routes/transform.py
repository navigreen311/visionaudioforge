"""Transform API — audio (and later video) transform endpoints."""

from __future__ import annotations

import base64
import io
import json
import time

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.responses import JSONResponse

from app.services.transform import AudioTransformService

router = APIRouter(prefix="/api/transform", tags=["transform"])

_svc = AudioTransformService()


@router.post("/audio")
async def transform_audio(
    file: UploadFile = File(...),
    operations: str = Form("[]"),
):
    """Apply a chain of audio transforms.

    *operations* is a JSON string — either:
    - a list of steps: ``[{"op": "denoise"}, {"op": "pitch", "params": {"semitones": 2}}]``
    - a preset object: ``{"preset": "podcast"}``
    """
    t0 = time.perf_counter()

    # --- read & decode audio ---
    try:
        raw = await file.read()
        buf = io.BytesIO(raw)
        audio, sr = sf.read(buf, dtype="float32")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot decode audio file: {exc}")

    # Ensure mono
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    original_duration = len(audio) / sr

    # --- parse operations ---
    try:
        ops = json.loads(operations)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON in operations: {exc}")

    # Preset shorthand
    if isinstance(ops, dict) and "preset" in ops:
        preset = ops["preset"]
        if preset == "podcast":
            ops = [{"op": "enhance"}]
        else:
            raise HTTPException(status_code=422, detail=f"Unknown preset: {preset}")

    if not isinstance(ops, list):
        raise HTTPException(status_code=422, detail="operations must be a JSON list or preset object")

    # --- apply chain ---
    try:
        result_audio, applied = _svc.apply_chain(audio, sr, ops)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transform error: {exc}")

    output_duration = len(result_audio) / sr

    # --- encode result as WAV base64 ---
    out_buf = io.BytesIO()
    sf.write(out_buf, result_audio, sr, format="WAV", subtype="FLOAT")
    wav_b64 = base64.b64encode(out_buf.getvalue()).decode()

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return JSONResponse(
        content={
            "audio": wav_b64,
            "format": "wav",
            "original_duration_s": round(original_duration, 4),
            "output_duration_s": round(output_duration, 4),
            "operations_applied": applied,
            "processing_time_ms": round(elapsed_ms, 2),
        }
    )
