"""Speech-to-text service using OpenAI Whisper."""

from __future__ import annotations

import io
import time

import librosa
import numpy as np
import soundfile as sf


class SpeechToTextService:
    """Transcribe audio using OpenAI Whisper (graceful fallback when unavailable)."""

    def __init__(self) -> None:
        self.available = False
        self._model = None
        try:
            import whisper  # noqa: F401

            self.available = True
        except ImportError:
            pass

    def _ensure_model(self):
        """Lazy-load the Whisper model on first use."""
        if self._model is None and self.available:
            import whisper

            self._model = whisper.load_model("base")

    async def transcribe(
        self,
        audio: np.ndarray,
        sr: int,
        language: str | None = None,
    ) -> dict:
        """Transcribe an audio array.

        Returns dict with keys: text, segments, language, duration_s.
        """
        duration_s = len(audio) / sr

        if not self.available:
            return {
                "text": "[Whisper not installed - pip install openai-whisper]",
                "segments": [],
                "language": "unknown",
                "duration_s": round(duration_s, 3),
            }

        self._ensure_model()

        # Whisper expects float32 mono at 16 kHz
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        audio = audio.astype(np.float32)

        options: dict = {}
        if language is not None:
            options["language"] = language

        result = self._model.transcribe(audio, **options)

        segments = [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "confidence": seg.get("avg_logprob", 0.0),
            }
            for seg in result.get("segments", [])
        ]

        return {
            "text": result.get("text", ""),
            "segments": segments,
            "language": result.get("language", "unknown"),
            "duration_s": round(duration_s, 3),
        }

    async def transcribe_file(self, file_bytes: bytes) -> dict:
        """Transcribe from raw audio file bytes."""
        buf = io.BytesIO(file_bytes)
        audio, sr = sf.read(buf, dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return await self.transcribe(audio, sr)

    async def detect_language(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict:
        """Detect the spoken language in an audio clip.

        Returns dict with keys: language, confidence.
        """
        if not self.available:
            return {"language": "unknown", "confidence": 0.0}

        self._ensure_model()
        import whisper

        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        audio = audio.astype(np.float32)

        # Pad/trim to 30 s as required by Whisper
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(self._model.device)
        _, probs = self._model.detect_language(mel)
        lang = max(probs, key=probs.get)
        return {"language": lang, "confidence": float(probs[lang])}
