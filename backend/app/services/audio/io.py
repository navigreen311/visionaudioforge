"""Audio I/O utilities: load, save, encode, and validate audio data."""

from __future__ import annotations

import base64
import io

import librosa
import numpy as np
import soundfile as sf


def load_audio(
    file_bytes: bytes,
    sr: int | None = None,
    mono: bool = True,
) -> tuple[np.ndarray, int]:
    """Load audio from raw bytes, returning (audio_array, sample_rate)."""
    buf = io.BytesIO(file_bytes)
    audio, orig_sr = sf.read(buf, dtype="float32")

    # Convert to mono if requested and audio is multi-channel
    if mono and audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    # Resample if a target sample rate is specified
    if sr is not None and sr != orig_sr:
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
        return audio, sr

    return audio, orig_sr


def save_audio(
    audio: np.ndarray,
    sr: int,
    format: str = "wav",
) -> bytes:
    """Write audio to bytes in the requested format."""
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format=format)
    buf.seek(0)
    return buf.read()


def audio_to_base64(
    audio: np.ndarray,
    sr: int,
    format: str = "wav",
) -> str:
    """Encode audio as a base64 string."""
    raw = save_audio(audio, sr, format=format)
    return base64.b64encode(raw).decode("utf-8")


def validate_audio(
    file_bytes: bytes,
    max_duration_s: float = 300,
    max_size_mb: float = 50,
) -> tuple[np.ndarray, int]:
    """Load audio and enforce size / duration limits.

    Raises ``ValueError`` when constraints are violated.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(
            f"File size {size_mb:.1f} MB exceeds limit of {max_size_mb} MB"
        )

    audio, sr = load_audio(file_bytes)

    duration = len(audio) / sr
    if duration > max_duration_s:
        raise ValueError(
            f"Audio duration {duration:.1f}s exceeds limit of {max_duration_s}s"
        )

    return audio, sr
