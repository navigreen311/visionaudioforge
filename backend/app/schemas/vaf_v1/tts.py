"""TTS request/response schemas for VAF v1 (PAF integration)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VAFVoice(BaseModel):
    """Mirror of the PAF-side ``VAFVoice`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    gender: str
    language: str
    accent: str
    style: str
    preview_url: str = Field(alias="previewUrl", serialization_alias="previewUrl")
    is_cloned: bool = Field(alias="isCloned", serialization_alias="isCloned")


class VAFSpeechRequest(BaseModel):
    """Mirror of the PAF-side ``VAFSpeechRequest`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    text: str
    voice: str
    speed: float = 1.0
    pitch: float = 0.0
    emotion: Optional[str] = "neutral"
    format: str = "mp3"
    sample_rate: int = Field(default=24000, alias="sampleRate")
    streaming: bool = False


class TTSStreamCreateRequest(BaseModel):
    """Request body for creating a TTS streaming session."""

    model_config = ConfigDict(populate_by_name=True)

    voice: str
    speed: float = 1.0
    pitch: float = 0.0
    emotion: Optional[str] = "neutral"
    format: str = "pcm"
    sample_rate: int = Field(default=24000, alias="sampleRate")
