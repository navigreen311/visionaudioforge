"""Audio-quality schemas for VAF v1 (PAF integration)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AudioQualityReport(BaseModel):
    """Mirror of the PAF-side ``AudioQualityReport`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    noise_level: float = Field(alias="noiseLevel", serialization_alias="noiseLevel")
    echo_detected: bool = Field(alias="echoDetected", serialization_alias="echoDetected")
    clipping_detected: bool = Field(
        alias="clippingDetected", serialization_alias="clippingDetected"
    )
    signal_to_noise: float = Field(
        alias="signalToNoise", serialization_alias="signalToNoise"
    )
    packet_loss: float = Field(alias="packetLoss", serialization_alias="packetLoss")
    bandwidth: str
    recommendation: str
