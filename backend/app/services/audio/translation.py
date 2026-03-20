"""Real-time audio translation stub: STT → translate → optional TTS."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from app.services.audio.stt import SpeechToTextService


class AudioTranslator:
    """Translate audio between languages (stub implementation).

    Real translation requires an external API (Google Translate, DeepL, etc.).
    Set ``TRANSLATION_API_KEY`` in your environment to enable a real backend.
    """

    def __init__(self) -> None:
        self._stt = SpeechToTextService()
        self._api_key = os.environ.get("TRANSLATION_API_KEY")

    # ------------------------------------------------------------------
    # Text translation stub
    # ------------------------------------------------------------------
    def translate_text(
        self, text: str, source_lang: str, target_lang: str
    ) -> dict[str, str]:
        """Translate text from *source_lang* to *target_lang*.

        V1 stub: returns original text unchanged with an explanatory note.
        """
        return {
            "translated_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "note": (
                "Real translation requires an external API "
                "(Google Translate, DeepL). Set TRANSLATION_API_KEY in env."
            ),
        }

    # ------------------------------------------------------------------
    # Audio translation
    # ------------------------------------------------------------------
    async def translate_audio(
        self, audio: np.ndarray, sr: int, source_lang: str, target_lang: str
    ) -> dict[str, Any]:
        """Translate speech in *audio*.

        Pipeline: STT → translate_text stub → return.
        No TTS synthesis for translated audio yet.
        """
        # Step 1: Speech-to-text
        stt_result = await self._stt.transcribe(audio, sr, language=source_lang)
        transcript = stt_result.get("text", "")

        # Step 2: Translate text (stub)
        translation = self.translate_text(transcript, source_lang, target_lang)

        return {
            "transcript": transcript,
            "translation": translation["translated_text"],
            "source_lang": source_lang,
            "target_lang": target_lang,
            "audio": None,  # TTS not yet implemented
            "note": translation["note"],
        }
