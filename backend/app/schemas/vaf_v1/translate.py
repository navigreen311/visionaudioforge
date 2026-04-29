"""Schemas for /api/v1/translate/*."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpeechTranslationResponse(BaseModel):
    """Response for /translate/speech. Matches PAF spec exactly.

    The request is sent as multipart/form-data with fields ``audio``,
    ``sourceLanguage`` and ``targetLanguage`` (no JSON schema required).
    """

    sourceText: str
    translatedText: str
    sourceLanguage: str
    confidence: float = Field(..., ge=0.0, le=1.0)
