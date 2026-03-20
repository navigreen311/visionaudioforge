"""Transform API routes — audio transforms AND video/image transforms.

Audio endpoints live under /api/transform/audio/...
Video endpoints live under /api/transform/video/...
"""

from __future__ import annotations

import base64
import io
import json
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.responses import JSONResponse

from app.services.transform.audio_transform import AudioTransformService
from app.services.transform.video_transform import VideoTransformService

router = APIRouter(prefix="/api/transform", tags=["transform"])

_audio_svc = AudioTransformService()
_video_svc = VideoTransformService()


# ===================================================================
# Helpers
# ===================================================================

async def _read_image(upload: UploadFile) -> np.ndarray:
    """Decode an uploaded file into a BGR numpy array."""
    data = await upload.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def _encode_png(image: np.ndarray) -> str:
    """Encode a numpy image to a base64 PNG string."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ===================================================================
# AUDIO TRANSFORM ENDPOINTS
# ===================================================================

@router.post("/audio/denoise")
async def audio_denoise(
    file: UploadFile = File(...),
    method: str = Form("spectral_gating"),
):
    """Denoise an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.denoise(audio, sr, method=method)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/silence-remove")
async def audio_silence_remove(file: UploadFile = File(...)):
    """Remove silence from an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.remove_silence(audio, sr)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "original_duration_s": round(len(audio) / sr, 4),
        "result_duration_s": round(len(result) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/pitch-shift")
async def audio_pitch_shift(
    file: UploadFile = File(...),
    semitones: float = Form(0.0),
):
    """Pitch-shift an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.pitch_shift(audio, sr, semitones=semitones)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "semitones": semitones,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/time-stretch")
async def audio_time_stretch(
    file: UploadFile = File(...),
    rate: float = Form(1.0),
):
    """Time-stretch an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.time_stretch(audio, sr, rate=rate)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "rate": rate,
        "original_duration_s": round(len(audio) / sr, 4),
        "result_duration_s": round(len(result) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/eq")
async def audio_eq(
    file: UploadFile = File(...),
    preset: str = Form("flat"),
):
    """Apply EQ preset to an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.apply_eq(audio, sr, preset=preset)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "preset": preset,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/chain")
async def audio_chain(
    file: UploadFile = File(...),
    steps: str = Form(...),
):
    """Apply a chain of audio transforms."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    try:
        parsed = json.loads(steps)
        if not isinstance(parsed, list):
            raise ValueError("steps must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result, applied = _audio_svc.apply_chain(audio, sr, parsed)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "applied": applied,
        "processing_time_ms": round(elapsed, 2),
    }


# ===================================================================
# VIDEO / IMAGE TRANSFORM ENDPOINTS
# ===================================================================

@router.post("/video/background-remove")
async def background_remove(
    file: UploadFile = File(...),
    method: str = Form("threshold"),
):
    start = time.perf_counter()
    image = await _read_image(file)
    result = _video_svc.remove_background(image, method=method)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "method": method,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/super-resolution")
async def super_resolution(
    file: UploadFile = File(...),
    scale: int = Form(2),
):
    start = time.perf_counter()
    image = await _read_image(file)
    h, w = image.shape[:2]
    result = _video_svc.super_resolution(image, scale=scale)
    rh, rw = result.shape[:2]
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "original_size": [w, h],
        "output_size": [rw, rh],
        "scale": scale,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/style")
async def style_transfer(
    file: UploadFile = File(...),
    style: str = Form("sketch"),
):
    start = time.perf_counter()
    image = await _read_image(file)
    result = _video_svc.style_transfer(image, style=style)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "style": style,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/auto-crop")
async def auto_crop(
    file: UploadFile = File(...),
    aspect: str = Form("16:9"),
):
    image = await _read_image(file)
    h, w = image.shape[:2]
    result = _video_svc.auto_crop(image, target_aspect=aspect)
    rh, rw = result.shape[:2]
    return {
        "image": _encode_png(result),
        "original_size": [w, h],
        "cropped_size": [rw, rh],
    }


@router.post("/video/thumbnail")
async def thumbnail(
    files: list[UploadFile] = File(...),
    method: str = Form("middle"),
):
    frames: list[np.ndarray] = []
    for f in files:
        frames.append(await _read_image(f))

    thumb, idx = _video_svc.generate_thumbnail(frames, method=method)
    return {
        "thumbnail": _encode_png(thumb),
        "frame_index": idx,
    }
