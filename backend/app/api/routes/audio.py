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
from app.services.audio.spectral import SpectralAnalyzer
from app.services.audio.visualization import (
    plot_mfcc,
    plot_mel_spectrogram,
    plot_spectrogram,
    plot_waveform,
)
from app.services.audio.stt import SpeechToTextService
from app.services.audio.vad import VoiceActivityDetector
from app.services.audio.separation import SourceSeparator
from app.services.audio.classification import AudioClassifier
from app.services.audio.voice_biometrics import VoiceBiometrics
from app.services.audio.fingerprinting import AudioFingerprinter
from app.services.audio.av_sync import AVSyncDetector
from app.services.audio.audio_embeddings import AudioEmbeddingService
from app.services.audio.translation import AudioTranslator

router = APIRouter(prefix="/api/audio", tags=["audio"])

_analyzer = SpectralAnalyzer()
_augmenter = AudioAugmenter()
_stt = SpeechToTextService()
_vad = VoiceActivityDetector()
_separator = SourceSeparator()
_classifier = AudioClassifier()
_biometrics = VoiceBiometrics()
_fingerprinter = AudioFingerprinter()
_av_sync = AVSyncDetector()
_embedder = AudioEmbeddingService()
_translator = AudioTranslator()


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    operations: str = Form('["all"]'),
):
    """Analyse an uploaded audio file with selectable spectral operations.

    *operations* is a JSON array of operation names. Supported values:
    ``"stft"``, ``"mel"``, ``"mfcc"``, ``"power"``, ``"waveform"``, ``"all"``.
    """
    start = time.perf_counter()

    # --- Load audio -------------------------------------------------------
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    # --- Parse requested operations ---------------------------------------
    try:
        ops = json.loads(operations)
        if not isinstance(ops, list):
            raise ValueError("operations must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid operations parameter: {exc}")

    run_all = "all" in ops

    # --- Run analyses -----------------------------------------------------
    features: dict = {}
    visualizations: dict = {}

    try:
        if run_all or "stft" in ops:
            stft = _analyzer.compute_stft(audio, sr)
            features["stft"] = {
                "shape": list(stft["magnitude"].shape),
                "freqs_count": len(stft["freqs"]),
                "times_count": len(stft["times"]),
            }
            visualizations["spectrogram"] = plot_spectrogram(stft["magnitude"], sr)

        if run_all or "mel" in ops:
            mel = _analyzer.compute_mel_spectrogram(audio, sr)
            features["mel"] = {
                "shape": list(mel["mel_spectrogram"].shape),
                "n_mels": mel["mel_spectrogram"].shape[0],
            }
            visualizations["mel_spectrogram"] = plot_mel_spectrogram(mel["mel_spectrogram"], sr)

        if run_all or "mfcc" in ops:
            mfcc = _analyzer.compute_mfcc(audio, sr)
            features["mfcc"] = {
                "shape": list(mfcc["mfcc"].shape),
                "n_mfcc": mfcc["mfcc"].shape[0],
            }
            visualizations["mfcc"] = plot_mfcc(mfcc["mfcc"], sr)

        if run_all or "power" in ops:
            power = _analyzer.compute_power_spectrogram(audio, sr)
            features["power"] = {
                "shape": list(power["power_spec"].shape),
            }

        if run_all or "waveform" in ops:
            waveform = _analyzer.compute_waveform_stats(audio, sr)
            features["waveform"] = waveform
            visualizations["waveform"] = plot_waveform(audio, sr)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio processing error: {exc}")

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "features": features,
        "visualizations": visualizations,
        "audio_info": {
            "sample_rate": sr,
            "duration_s": round(len(audio) / sr, 4),
            "samples": len(audio),
        },
        "processing_time_ms": round(elapsed_ms, 2),
    }


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
    model: str = Form("base"),
    language: str = Form("auto"),
    task: str = Form("transcribe"),
    word_timestamps: bool = Form(True),
):
    """Transcribe speech in an uploaded audio file using Whisper.

    Parameters
    ----------
    file : UploadFile
        Audio file to transcribe.
    model : str
        Whisper model size (tiny/base/small/medium/large). Default ``"base"``.
    language : str
        Language code or ``"auto"`` for auto-detection. Default ``"auto"``.
    task : str
        ``"transcribe"`` or ``"translate"`` (translate to English). Default ``"transcribe"``.
    word_timestamps : bool
        Whether to include word-level timestamps. Default ``True``.

    Returns
    -------
    dict
        ``{ "transcript": "", "words": [], "language": "en", "speakers": [], "duration_sec": 0.0 }``
    """
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    lang_arg = None if language == "auto" else language
    result = await _stt.transcribe(
        audio,
        sr,
        language=lang_arg,
        model=model,
        task=task,
        word_timestamps=word_timestamps,
    )
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


# ---------------------------------------------------------------------------
# Voice Biometrics
# ---------------------------------------------------------------------------


@router.post("/voiceprint")
async def voiceprint(file: UploadFile = File(...)):
    """Extract a 128-dim voiceprint from an uploaded audio file."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    vp = _biometrics.extract_voiceprint(audio, sr)
    return {"voiceprint": vp.tolist(), "dimensions": len(vp)}


@router.post("/voiceprint/compare")
async def voiceprint_compare(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare voiceprints of two audio files."""
    try:
        bytes1 = await file1.read()
        audio1, sr1 = librosa.load(io.BytesIO(bytes1), sr=None)
        bytes2 = await file2.read()
        audio2, sr2 = librosa.load(io.BytesIO(bytes2), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    vp1 = _biometrics.extract_voiceprint(audio1, sr1)
    vp2 = _biometrics.extract_voiceprint(audio2, sr2)
    result = _biometrics.compare_voiceprints(vp1, vp2)
    return result


# ---------------------------------------------------------------------------
# Audio Fingerprinting
# ---------------------------------------------------------------------------


@router.post("/fingerprint")
async def fingerprint(file: UploadFile = File(...)):
    """Generate an acoustic fingerprint for an uploaded audio file."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    fp = _fingerprinter.generate_fingerprint(audio, sr)
    return {
        "fingerprint": fp["fingerprint"],
        "duration_s": fp["duration_s"],
        "peaks": fp["peaks"],
    }


@router.post("/fingerprint/match")
async def fingerprint_match(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare fingerprints of two audio files."""
    try:
        bytes1 = await file1.read()
        audio1, sr1 = librosa.load(io.BytesIO(bytes1), sr=None)
        bytes2 = await file2.read()
        audio2, sr2 = librosa.load(io.BytesIO(bytes2), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    fp1 = _fingerprinter.generate_fingerprint(audio1, sr1)
    fp2 = _fingerprinter.generate_fingerprint(audio2, sr2)
    result = _fingerprinter.match_fingerprints(fp1, fp2)
    return {
        "match": result["match"],
        "similarity": result["similarity"],
        "offset_s": result["offset_s"],
    }


# ---------------------------------------------------------------------------
# AV Sync Detection
# ---------------------------------------------------------------------------


@router.post("/av-sync")
async def av_sync(
    file: UploadFile = File(...),
    fps: float = Form(30.0),
):
    """Detect audio-video sync offset.

    Expects an audio file. Video frame brightness data is extracted
    from the audio energy envelope for demonstration purposes.
    """
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    # Generate synthetic video frames from audio for demo
    samples_per_frame = int(sr / fps)
    n_frames = len(audio) // samples_per_frame
    video_frames = [
        np.array([np.sqrt(np.mean(audio[i * samples_per_frame : (i + 1) * samples_per_frame] ** 2))])
        for i in range(n_frames)
    ]

    result = _av_sync.detect_sync_offset(video_frames, audio, sr, fps)
    return result


# ---------------------------------------------------------------------------
# Audio Embeddings
# ---------------------------------------------------------------------------


@router.post("/embed")
async def embed(
    file: UploadFile = File(...),
    model: str = Form("mfcc_stats"),
):
    """Generate a 512-dim embedding for an uploaded audio file."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    embedding = _embedder.embed_audio(audio, sr, model=model)
    return {"embedding": embedding.tolist(), "dimensions": len(embedding), "model": model}


# ---------------------------------------------------------------------------
# Audio Translation
# ---------------------------------------------------------------------------


@router.post("/translate")
async def translate(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("es"),
):
    """Translate speech in an uploaded audio file (stub)."""
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode audio file: {exc}")

    result = await _translator.translate_audio(audio, sr, source_lang, target_lang)
    # Remove numpy array from response (not JSON-serializable)
    result.pop("audio", None)
    return result
