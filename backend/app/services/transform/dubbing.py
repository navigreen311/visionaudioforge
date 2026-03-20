"""Auto-dubbing service — STT -> translate -> TTS pipeline.

V1 uses stubs for STT and translation; TTS uses the placeholder service.
"""

from __future__ import annotations

import numpy as np

from app.services.transform.tts import TTSService

_tts = TTSService()

# Stub language-specific speaking rates (chars/sec)
_LANG_RATES: dict[str, float] = {
    "en": 4.0,
    "es": 4.5,
    "fr": 4.2,
    "de": 3.8,
    "ja": 3.0,
    "zh": 3.0,
    "ko": 3.5,
    "pt": 4.3,
    "it": 4.4,
    "ru": 3.9,
}


class AutoDubber:
    """Auto-dubbing: STT -> translate -> TTS."""

    def dub_audio(
        self,
        audio: np.ndarray,
        sr: int,
        source_lang: str = "en",
        target_lang: str = "es",
        voice: str = "default",
    ) -> dict:
        """Dub audio from source language to target language.

        Pipeline:
        1. STT (Whisper if available, otherwise stub)
        2. Translate (stub)
        3. TTS (placeholder tone synthesis)
        """
        # Step 1: STT
        transcript = self._stt(audio, sr, source_lang)

        # Step 2: Translate
        translated = self._translate(transcript, source_lang, target_lang)

        # Step 3: TTS
        dubbed_audio, tts_sr = _tts.synthesize(translated, voice=voice)

        # Resample to match original sr if different
        if tts_sr != sr:
            duration = len(dubbed_audio) / tts_sr
            n_samples = int(duration * sr)
            dubbed_audio = np.interp(
                np.linspace(0, len(dubbed_audio) - 1, n_samples),
                np.arange(len(dubbed_audio)),
                dubbed_audio,
            ).astype(np.float32)

        return {
            "dubbed_audio": dubbed_audio,
            "original_transcript": transcript,
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "note": (
                "V1 stub pipeline. STT uses Whisper if available, "
                "otherwise returns placeholder transcript. "
                "Translation is a stub. TTS uses tone-based placeholder."
            ),
        }

    def estimate_dubbing_duration(self, text: str, target_lang: str) -> float:
        """Estimate how long the dubbed audio will be in seconds."""
        rate = _LANG_RATES.get(target_lang, 4.0)
        return max(len(text) / rate, 0.1)

    def _stt(self, audio: np.ndarray, sr: int, lang: str) -> str:
        """Speech-to-text — try Whisper, fall back to stub."""
        try:
            import whisper  # type: ignore[import-untyped]

            model = whisper.load_model("base")
            # Whisper expects float32, 16kHz
            if sr != 16000:
                duration = len(audio) / sr
                n_samples = int(duration * 16000)
                audio_16k = np.interp(
                    np.linspace(0, len(audio) - 1, n_samples),
                    np.arange(len(audio)),
                    audio,
                ).astype(np.float32)
            else:
                audio_16k = audio.astype(np.float32)

            result = model.transcribe(audio_16k, language=lang)
            return result.get("text", "")
        except (ImportError, Exception):
            duration_s = len(audio) / sr
            return f"[Transcribed audio — {duration_s:.1f}s of {lang} speech]"

    def _translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text — stub implementation."""
        if source_lang == target_lang:
            return text
        return f"[{target_lang}] {text}"
