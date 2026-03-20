"""Audio API routes: spectral analysis, augmentation."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import JSONResponse

from app.schemas.audio import AudioAnalyzeResponse, AudioFeatureResult
from app.services.audio.io import validate_audio
from app.services.audio.spectral import SpectralAnalyzer
from app.services.audio.visualization import (
    plot_mel_spectrogram,
    plot_mfcc,
    plot_spectrogram,
    plot_waveform,
)

router = APIRouter(prefix="/api/audio", tags=["audio"])

_analyzer = SpectralAnalyzer()


@router.post("/analyze", response_model=AudioAnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    operations: str = Form(default='["all"]'),
):
    """Analyze an uploaded audio file.

    ``operations`` is a JSON-encoded list, e.g. ``'["stft","mel","mfcc","waveform"]'``
    or ``'["all"]'``.
    """
    start = time.perf_counter()

    ops: list[str] = json.loads(operations)
    run_all = "all" in ops

    file_bytes = await file.read()
    audio, sr = validate_audio(file_bytes)

    features: dict[str, AudioFeatureResult] = {}

    # --- STFT ---
    if run_all or "stft" in ops:
        stft_result = _analyzer.compute_stft(audio, sr)
        viz = plot_spectrogram(stft_result["magnitude"], sr)
        features["stft"] = AudioFeatureResult(
            shape=list(stft_result["magnitude"].shape),
            visualization=viz,
        )

    # --- MEL ---
    if run_all or "mel" in ops:
        mel_result = _analyzer.compute_mel_spectrogram(audio, sr)
        viz = plot_mel_spectrogram(mel_result["mel_spectrogram"], sr)
        features["mel"] = AudioFeatureResult(
            shape=list(mel_result["mel_spectrogram"].shape),
            visualization=viz,
        )

    # --- MFCC ---
    if run_all or "mfcc" in ops:
        mfcc_result = _analyzer.compute_mfcc(audio, sr)
        viz = plot_mfcc(mfcc_result["mfcc"], sr)
        features["mfcc"] = AudioFeatureResult(
            shape=list(mfcc_result["mfcc"].shape),
            visualization=viz,
            coefficients=mfcc_result["mfcc"].tolist(),
        )

    # --- POWER ---
    if run_all or "power" in ops:
        power_result = _analyzer.compute_power_spectrogram(audio, sr)
        features["power"] = AudioFeatureResult(
            shape=list(power_result["power_spec"].shape),
        )

    # --- WAVEFORM ---
    if run_all or "waveform" in ops:
        stats = _analyzer.compute_waveform_stats(audio, sr)
        viz = plot_waveform(audio, sr)
        features["waveform"] = AudioFeatureResult(
            visualization=viz,
            stats=stats,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    waveform_stats = _analyzer.compute_waveform_stats(audio, sr)

    return AudioAnalyzeResponse(
        features=features,
        audio_info={
            "duration_s": waveform_stats["duration_s"],
            "sample_rate": waveform_stats["sample_rate"],
            "samples": waveform_stats["samples"],
        },
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post("/augment")
async def augment():
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "module": "audio"},
    )
