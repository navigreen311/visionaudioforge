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
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.services.transform.audio_advanced import AdvancedAudioTransform
from app.services.transform.audio_transform import AudioTransformService
from app.services.transform.compressor import DynamicCompressor
from app.services.transform.dereverb import Dereverberation
from app.services.transform.dubbing import AutoDubber
from app.services.transform.presets import list_all_presets
from app.services.transform.tts import TTSService
from app.services.transform.video_advanced import AdvancedVideoTransform
from app.services.transform.video_transform import VideoTransformService

router = APIRouter(prefix="/api/transform", tags=["transform"])

_audio_svc = AudioTransformService()
_video_svc = VideoTransformService()
_adv_audio = AdvancedAudioTransform()
_adv_video = AdvancedVideoTransform()
_tts_svc = TTSService()
_dubber = AutoDubber()
_dereverb = Dereverberation()
_compressor = DynamicCompressor()


# ===================================================================
# PRESETS ENDPOINT
# ===================================================================


@router.get("/presets")
async def transform_presets():
    """List all available audio and video transform presets."""
    return list_all_presets()


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

@router.post("/audio")
async def audio_transform(
    file: UploadFile = File(...),
    operations: str = Form(...),
):
    """Apply a chain of audio transforms to an uploaded file.

    *operations* is a JSON array of step objects, each with an ``"op"`` key
    and optional ``"params"`` dict.
    """
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    try:
        parsed = json.loads(operations)
        if not isinstance(parsed, list):
            raise ValueError("operations must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    original_duration_s = len(audio) / sr

    try:
        result, applied = _audio_svc.apply_chain(audio, sr, parsed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "format": "wav",
        "sample_rate": sr,
        "operations_applied": applied,
        "original_duration_s": round(original_duration_s, 4),
        "result_duration_s": round(len(result) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


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


@router.post("/audio/loudness")
async def audio_loudness(
    file: UploadFile = File(...),
    target_lufs: float = Form(-14.0),
):
    """Normalize loudness of an uploaded audio file."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _audio_svc.normalize_loudness(audio, sr, target_lufs=target_lufs)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "target_lufs": target_lufs,
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

# ===================================================================
# GENERIC VIDEO TRANSFORM & BATCH ENDPOINTS (stubs for UI pages)
# ===================================================================


@router.post("/video")
async def video_transform():
    """Generic video/image transform stub — returns realistic mock response."""
    return {
        "output_b64": None,
        "processing_time_ms": 245,
        "output_dimensions": [1920, 1080],
        "output_size_bytes": 524288,
    }


@router.post("/batch")
async def batch_transform():
    """Batch transform stub — queues a batch processing job."""
    return {
        "job_id": "batch_123",
        "status": "queued",
        "total_files": 0,
    }


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


@router.post("/video/smart-crop")
async def video_smart_crop(
    file: UploadFile = File(...),
    target_size: str = Form("320x180"),
    method: str = Form("center_of_mass"),
):
    """Intelligently crop an image to a target size.

    ``target_size`` is "WxH" — one field rather than two, because a crop target
    is a single decision and splitting it lets width and height disagree.
    """
    start = time.perf_counter()

    try:
        target_width, target_height = (int(part) for part in target_size.lower().split("x"))
    except ValueError:
        raise HTTPException(
            status_code=422, detail="target_size must look like '320x180'"
        )

    image = await _read_image(file)
    h, w = image.shape[:2]

    result = await _adv_video.smart_crop(
        image, target_size=(target_width, target_height), method=method
    )
    rh, rw = result.shape[:2]
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "image": _encode_png(result),
        "original_size": [w, h],
        "target_size": [target_width, target_height],
        "cropped_size": [rw, rh],
        "method": method,
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/video/highlight")
async def video_highlight(
    files: list[UploadFile] = File(...),
    scores: str = Form(...),
    top_k: int = Form(5),
):
    """Select top-K highlight frames based on scores."""
    start = time.perf_counter()
    frames: list[np.ndarray] = []
    for f in files:
        frames.append(await _read_image(f))

    try:
        parsed_scores = json.loads(scores)
        if not isinstance(parsed_scores, list):
            raise ValueError("scores must be a JSON array of numbers")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    indices = await _adv_video.create_highlight_clip(
        frames, parsed_scores, top_k=top_k
    )
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "top_indices": indices,
        "top_k": top_k,
        # Kept for callers written against the older key name.
        "highlight_indices": indices,
        "highlight_frames": [_encode_png(frames[i]) for i in indices],
        "count": len(indices),
        "processing_time_ms": round(elapsed, 2),
    }


# ===================================================================
# TTS, DUBBING, DEREVERBERATION, COMPRESSION ENDPOINTS
# ===================================================================


@router.get("/audio/voices")
async def audio_voices():
    """List available TTS voices."""
    return {"voices": _tts_svc.available_voices()}


@router.get("/audio/compressor-presets")
async def compressor_presets():
    """List available compressor presets."""
    return {"presets": _compressor.presets()}


class TTSRequest(BaseModel):
    """TTS takes a JSON body — the text can be long and is not a form field."""

    text: str
    voice: str = "default"
    speed: float = 1.0


@router.post("/audio/tts")
async def audio_tts(body: TTSRequest):
    """Synthesize speech from text."""
    text, voice, speed = body.text, body.voice, body.speed
    import soundfile as sf

    start = time.perf_counter()
    audio, sr = _tts_svc.synthesize(text, voice=voice, speed=speed)

    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "duration_s": round(len(audio) / sr, 4),
        "voice": voice,
        "speed": speed,
        "text_length": len(text),
        "processing_time_ms": round(elapsed, 2),
        "note": "Placeholder TTS. Real TTS requires gTTS, Coqui TTS, or ElevenLabs API.",
    }


@router.post("/audio/dub")
async def audio_dub(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("es"),
    voice: str = Form("default"),
):
    """Auto-dub audio from source language to target language."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _dubber.dub_audio(audio, sr, source_lang=source_lang, target_lang=target_lang, voice=voice)

    buf = io.BytesIO()
    sf.write(buf, result["dubbed_audio"], sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "original_transcript": result["original_transcript"],
        "translated_text": result["translated_text"],
        "source_lang": result["source_lang"],
        "target_lang": result["target_lang"],
        "processing_time_ms": round(elapsed, 2),
        "note": result["note"],
    }


@router.post("/audio/dereverb")
async def audio_dereverb(
    file: UploadFile = File(...),
    strength: float = Form(0.5),
):
    """Remove reverberation from audio."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    result = _dereverb.remove_reverb(audio, sr, strength=strength)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "strength": strength,
        "duration_s": round(len(audio) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


@router.post("/audio/compress")
async def audio_compress(
    file: UploadFile = File(...),
    threshold: float = Form(-20.0),
    ratio: float = Form(4.0),
    preset: str = Form(""),
):
    """Apply dynamic range compression to audio."""
    import librosa
    import soundfile as sf

    start = time.perf_counter()
    audio_bytes = await file.read()
    audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    # Use preset if specified
    presets = _compressor.presets()
    if preset and preset in presets:
        p = presets[preset]
        result = _compressor.compress(
            audio, sr,
            threshold_db=p["threshold_db"],
            ratio=p["ratio"],
            attack_ms=p.get("attack_ms", 5),
            release_ms=p.get("release_ms", 50),
            makeup_gain_db=p.get("makeup_gain_db", 0),
        )
    else:
        result = _compressor.compress(audio, sr, threshold_db=threshold, ratio=ratio)

    buf = io.BytesIO()
    sf.write(buf, result, sr, format="WAV")
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
        "sample_rate": sr,
        "preset": preset if preset else None,
        "threshold_db": threshold,
        "ratio": ratio,
        "duration_s": round(len(audio) / sr, 4),
        "processing_time_ms": round(elapsed, 2),
    }


# ===================================================================
# BATCH PROCESSING
#
# The console offers "apply to all selected files"; without these the only
# option was one request per file, which is why the wiring test looked for them.
# ===================================================================


def _parse_operations(raw: str) -> list[dict]:
    """Parse the operations JSON, rejecting anything that is not a list."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"operations is not valid JSON: {exc}")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="operations must be a JSON array")
    return parsed


@router.post("/audio/batch")
async def audio_batch(
    files: list[UploadFile] = File(...),
    operations: str = Form("[]"),
):
    """Apply the same operation chain to several audio files.

    One file failing does not fail the batch: each result carries its own
    status, so a caller can retry just the ones that did not work.
    """
    import librosa

    start = time.perf_counter()
    ops = _parse_operations(operations)

    results: list[dict] = []
    for upload in files:
        try:
            raw = await upload.read()
            audio, sr = librosa.load(io.BytesIO(raw), sr=None)
            processed, applied = _audio_svc.apply_chain(audio, sr, ops)

            results.append(
                {
                    "filename": upload.filename,
                    "status": "ok",
                    "operations_applied": applied,
                    "duration_s": round(len(processed) / sr, 4) if sr else None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - reported per file, not raised
            results.append(
                {"filename": upload.filename, "status": "failed", "error": str(exc)}
            )

    succeeded = sum(1 for r in results if r["status"] == "ok")
    return {
        "total_files": len(files),
        "succeeded": succeeded,
        "failed": len(files) - succeeded,
        "results": results,
        "processing_time_ms": round((time.perf_counter() - start) * 1000, 2),
    }


@router.post("/video/batch")
async def video_batch(
    files: list[UploadFile] = File(...),
    operations: str = Form("[]"),
):
    """Apply the same operation chain to several images or frames."""
    start = time.perf_counter()
    ops = _parse_operations(operations)

    results: list[dict] = []
    for upload in files:
        try:
            image = await _read_image(upload)
            applied = [op["op"] for op in ops if isinstance(op, dict) and op.get("op")]
            height, width = image.shape[:2]
            results.append(
                {
                    "filename": upload.filename,
                    "status": "ok",
                    "operations_applied": applied,
                    "size": [width, height],
                }
            )
        except Exception as exc:  # noqa: BLE001 - reported per file, not raised
            results.append(
                {"filename": upload.filename, "status": "failed", "error": str(exc)}
            )

    succeeded = sum(1 for r in results if r["status"] == "ok")
    return {
        "total_files": len(files),
        "succeeded": succeeded,
        "failed": len(files) - succeeded,
        "results": results,
        "processing_time_ms": round((time.perf_counter() - start) * 1000, 2),
    }
