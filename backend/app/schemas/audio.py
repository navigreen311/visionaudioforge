"""Pydantic schemas for audio spectral analysis endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AudioAnalyzeRequest(BaseModel):
    """Body schema parsed from the ``operations`` form field."""

    operations: list[str] = Field(
        default=["all"],
        description='List of operations: "stft", "mel", "mfcc", "waveform", "power", or "all".',
    )


class AudioFeatureResult(BaseModel):
    """Result container for a single audio feature."""

    shape: list[int] | None = None
    visualization: str | None = None
    stats: dict | None = None
    coefficients: list[list[float]] | None = None


class AudioAnalyzeResponse(BaseModel):
    """Top-level response for POST /api/audio/analyze."""

    features: dict[str, AudioFeatureResult]
    audio_info: dict
    processing_time_ms: float
