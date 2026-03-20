"""Pydantic schemas for audio augmentation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AugmentationStep(BaseModel):
    """A single augmentation step in a pipeline configuration."""

    type: str = Field(..., description="Augmentation type: noise, stretch, pitch, or shift")
    probability: float = Field(1.0, ge=0.0, le=1.0, description="Probability of applying this step")
    params: dict = Field(default_factory=dict, description="Parameters forwarded to the augmentation method")


class AugmentConfig(BaseModel):
    """Request body for the augment endpoint (used when sent as JSON body)."""

    steps: list[AugmentationStep] | None = None
    preset: str | None = None


class AudioAugmentResponse(BaseModel):
    """Response from the augment endpoint."""

    augmented_audio: str = Field(..., description="Base64-encoded augmented WAV audio")
    applied_augmentations: list[dict] = Field(default_factory=list, description="List of augmentations that were applied")
    original_duration_s: float = Field(..., description="Duration of the original audio in seconds")
    augmented_duration_s: float = Field(..., description="Duration of the augmented audio in seconds")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
