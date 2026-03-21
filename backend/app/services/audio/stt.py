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
        self._models: dict = {}
        try:
            import whisper  # noqa: F401

            self.available = True
        except ImportError:
            pass

    def _ensure_model(self, model_name: str = "base"):
        """Lazy-load the Whisper model on first use."""
        if model_name not in self._models and self.available:
            import whisper

            self._models[model_name] = whisper.load_model(model_name)
        return self._models.get(model_name)

    async def transcribe(
        self,
        audio: np.ndarray,
        sr: int,
        language: str | None = None,
        model: str = "base",
        task: str = "transcribe",
        word_timestamps: bool = True,
    ) -> dict:
        """Transcribe an audio array.

        Returns dict with keys:
            transcript, text, segments, words, language, speakers, duration_sec.
        """
        duration_s = len(audio) / sr

        if not self.available:
            return {
                "transcript": "[Whisper not installed - pip install openai-whisper]",
                "text": "[Whisper not installed - pip install openai-whisper]",
                "segments": [],
                "words": [],
                "language": "unknown",
                "speakers": [],
                "duration_sec": round(duration_s, 3),
            }

        whisper_model = self._ensure_model(model)

        # Whisper expects float32 mono at 16 kHz
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

        audio = audio.astype(np.float32)

        options: dict = {"task": task, "word_timestamps": word_timestamps}
        if language is not None:
            options["language"] = language

        result = whisper_model.transcribe(audio, **options)

        segments = [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "confidence": seg.get("avg_logprob", 0.0),
            }
            for seg in result.get("segments", [])
        ]

        # Extract word-level timestamps if available
        words: list[dict] = []
        if word_timestamps:
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    words.append(
                        {
                            "word": w.get("word", "").strip(),
                            "start": round(w.get("start", 0.0), 3),
                            "end": round(w.get("end", 0.0), 3),
                        }
                    )

        full_text = result.get("text", "")
        detected_language = result.get("language", "unknown")

        return {
            "transcript": full_text,
            "text": full_text,
            "segments": segments,
            "words": words,
            "language": detected_language,
            "speakers": [],
            "duration_sec": round(duration_s, 3),
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

        whisper_model = self._ensure_model("base")
        import whisper

        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        audio = audio.astype(np.float32)

        # Pad/trim to 30 s as required by Whisper
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(whisper_model.device)
        _, probs = whisper_model.detect_language(mel)
        lang = max(probs, key=probs.get)
        return {"language": lang, "confidence": float(probs[lang])}
