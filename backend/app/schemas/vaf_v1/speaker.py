"""Speaker-ID / voiceprint schemas for VAF v1 (PAF integration)."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class VoiceprintEnrollment(BaseModel):
    """Mirror of the PAF-side ``VoiceprintEnrollment`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId", serialization_alias="userId")
    sample_urls: List[str] = Field(alias="sampleUrls", serialization_alias="sampleUrls")
    quality_scores: List[float] = Field(
        alias="qualityScores", serialization_alias="qualityScores"
    )
    enrolled: bool
    enrolled_at: str = Field(alias="enrolledAt", serialization_alias="enrolledAt")


class AntiSpoofResult(BaseModel):
    """Anti-spoof verification metadata."""

    model_config = ConfigDict(populate_by_name=True)

    is_live_voice: bool = Field(alias="isLiveVoice", serialization_alias="isLiveVoice")
    is_not_synthesized: bool = Field(
        alias="isNotSynthesized", serialization_alias="isNotSynthesized"
    )
    confidence: float


class VoiceprintVerification(BaseModel):
    """Mirror of the PAF-side ``VoiceprintVerification`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    match: bool
    confidence: float
    threshold: float = 0.85
    latency_ms: float = Field(alias="latencyMs", serialization_alias="latencyMs")
    anti_spoof_result: AntiSpoofResult = Field(
        alias="antiSpoofResult", serialization_alias="antiSpoofResult"
    )


class SpeakerContinuousRequest(BaseModel):
    """Request body for creating a continuous speaker-ID session."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")
    threshold: float = 0.85
    check_interval_seconds: int = Field(default=30, alias="checkIntervalSeconds")
    enable_anti_spoof: bool = Field(default=True, alias="enableAntiSpoof")
