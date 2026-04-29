"""VAF v1 — Translation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.schemas.vaf_v1.translate import SpeechTranslationResponse

from ._auth_shim import vaf_auth

router = APIRouter(prefix="/api/v1/translate", tags=["vaf-v1-translate"])


@router.post("/speech", response_model=SpeechTranslationResponse)
async def translate_speech(
    audio: UploadFile = File(...),
    sourceLanguage: str = Form(...),
    targetLanguage: str = Form(...),
    _token: str = Depends(vaf_auth),
) -> SpeechTranslationResponse:
    """Translate speech audio from a source language to a target language.

    Mock contract — echoes back a fixture that lets the PAF client
    exercise the response shape end-to-end. The detected source language
    is reported back as ``sourceLanguage`` per the spec, defaulting to
    the requested source if auto-detection is not active.
    """
    await audio.read()

    detected = sourceLanguage if sourceLanguage and sourceLanguage != "auto" else "es"

    return SpeechTranslationResponse(
        sourceText="hola",
        translatedText=f"(translated from {detected}) hello",
        sourceLanguage=detected,
        confidence=0.94,
    )
