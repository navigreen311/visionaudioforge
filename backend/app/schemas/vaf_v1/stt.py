"""STT request/response schemas for VAF v1 (PAF integration)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WordTiming(BaseModel):
    """Per-word timing metadata returned in transcription results."""

    model_config = ConfigDict(populate_by_name=True)

    word: str
    start: float
    end: float
    confidence: float
    speaker: Optional[str] = None


class VAFTranscriptionResult(BaseModel):
    """Mirror of the PAF-side ``VAFTranscriptionResult`` TypeScript interface."""

    model_config = ConfigDict(populate_by_name=True)

    text: str
    confidence: float
    is_final: bool = Field(default=True, alias="isFinal", serialization_alias="isFinal")
    words: List[WordTiming]
    language: str
    latency_ms: float = Field(alias="latencyMs", serialization_alias="latencyMs")


class STTStreamCreateRequest(BaseModel):
    """Request body for creating an STT streaming session."""

    model_config = ConfigDict(populate_by_name=True)

    language: str = "en-US"
    model: str = "realtime"
    enable_speaker_diarization: bool = Field(
        default=False, alias="enableSpeakerDiarization"
    )
    custom_vocabulary: List[str] = Field(default_factory=list, alias="customVocabulary")
    compliance_mode: List[str] = Field(default_factory=list, alias="complianceMode")
    interim_results: bool = Field(default=True, alias="interimResults")
    punctuation: bool = True
    profanity_filter: bool = Field(default=False, alias="profanityFilter")


class StreamSessionResponse(BaseModel):
    """Response for stream/create endpoints (STT, TTS, speaker continuous)."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", serialization_alias="sessionId")
    websocket_url: str = Field(alias="websocketUrl", serialization_alias="websocketUrl")
