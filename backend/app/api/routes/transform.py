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

from app.services.transform.audio_advanced import AdvancedAudioTransform
from app.services.transform.audio_transform import AudioTransformService
from app.services.transform.video_advanced import AdvancedVideoTransform
from app.services.transform.video_transform import VideoTransformService

router = APIRouter(prefix="/api/transform", tags=["transform"])

_audio_svc = AudioTransformService()
_video_svc = VideoTransformService()
_adv_audio = AdvancedAudioTransform()
_adv_video = AdvancedVideoTransform()


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


# ===================================================================
# ADVANCED AUDIO ENDPOINTS
# ===================================================================


@router.post("/audio/voice-convert")
async def audio_voice_convert(
    file: UploadFile = File(...),
    target_voice: str = Form("male_deep"),
):
    """Convert voice using pitch shift + formant approximation."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = await _adv_audio.voice_conversion_stub(audio, sr, target_voice=target_voice)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "target_voice": target_voice,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/chapters")
async def audio_chapters(
    file: UploadFile = File(...),
    min_silence: float = Form(2.0),
):
    """Detect chapters by finding long silences."""
    import librosa

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    chapters = await _adv_audio.auto_chapter(audio, sr, min_silence_s=min_silence)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "duration_s": round(len(audio) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/noise-profile")
async def audio_noise_profile(
    file: UploadFile = File(...),
):
    """Analyze noise profile of the audio file."""
    import librosa

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    profile = await _adv_audio.noise_profile(audio, sr)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        **profile,
        "sample_rate": sr,
        "processing_time_ms": round(elapsed, 2),
    }


# ===================================================================
# ADVANCED VIDEO ENDPOINTS
# ===================================================================


@router.post("/video/inpaint")
async def video_inpaint(
    file: UploadFile = File(...),
    mask: UploadFile = File(...),
):
    """Inpaint image regions specified by a mask."""
    start = time.perf_counter()
    image = await _read_image(file)

    mask_data = await mask.read()
    mask_arr = np.frombuffer(mask_data, np.uint8)
    mask_img = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        raise HTTPException(status_code=400, detail="Could not decode mask image")

    result = await _adv_video.inpaint(image, mask_img)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "image": _encode_png(result),
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/color-grade")
async def video_color_grade(
    file: UploadFile = File(...),
    preset: str = Form("cinematic"),
):
    """Apply color grading preset to an image."""
    start = time.perf_counter()
    image = await _read_image(file)
    result = await _adv_video.color_grade(image, preset=preset)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "image": _encode_png(result),
        "preset": preset,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/subtitle")
async def video_subtitle(
    file: UploadFile = File(...),
    text: str = Form(...),
    position: str = Form("bottom"),
):
    """Burn subtitle text onto an image."""
    start = time.perf_counter()
    image = await _read_image(file)
    result = await _adv_video.subtitle_burn(image, text=text, position=position)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "image": _encode_png(result),
        "text": text,
        "position": position,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/interpolate")
async def video_interpolate(
    frame1: UploadFile = File(...),
    frame2: UploadFile = File(...),
    count: int = Form(1),
):
    """Generate intermediate frames between two input frames."""
    start = time.perf_counter()
    img1 = await _read_image(frame1)
    img2 = await _read_image(frame2)

    intermediates = await _adv_video.frame_interpolation(img1, img2, num_intermediate=count)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "frames": [_encode_png(f) for f in intermediates],
        "count": len(intermediates),
        "processing_time_ms": round(elapsed, 2),
    }
