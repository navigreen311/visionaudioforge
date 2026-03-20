"""Keyword spotting and wake word detection for audio streams."""

from __future__ import annotations

from typing import Callable

import numpy as np

from app.services.audio.stt import SpeechToTextService


class KeywordSpotter:
    """Spot keywords in audio using transcript-based matching."""

    def __init__(self) -> None:
        self._stt = SpeechToTextService()

    async def spot_keywords(
        self,
        audio: np.ndarray,
        sr: int,
        keywords: list[str],
        method: str = "transcript",
    ) -> list[dict]:
        """Find keyword occurrences in audio with timestamps.

        Args:
            audio: Audio signal as numpy array.
            sr: Sample rate.
            keywords: List of keywords to search for.
            method: Detection method ('transcript' uses STT then string search).

        Returns:
            List of dicts with keyword, start_s, end_s, confidence.
        """
        if not keywords:
            return []

        if method != "transcript":
            raise ValueError(f"Unsupported method: {method}. Use 'transcript'.")

        # Transcribe the audio
        transcription = await self._stt.transcribe(audio, sr)
        segments = transcription.get("segments", [])

        if not segments:
            # Fallback: check full text
            full_text = transcription.get("text", "").lower()
            results = []
            duration_s = len(audio) / sr
            for kw in keywords:
                if kw.lower() in full_text:
                    results.append(
                        {
                            "keyword": kw,
                            "start_s": 0.0,
                            "end_s": round(duration_s, 3),
                            "confidence": 0.5,
                        }
                    )
            return results

        # Search each segment for keyword matches
        results: list[dict] = []
        keywords_lower = [kw.lower() for kw in keywords]

        for seg in segments:
            seg_text = seg.get("text", "").lower()
            seg_start = seg.get("start", 0.0)
            seg_end = seg.get("end", 0.0)
            seg_confidence = seg.get("confidence", 0.0)

            # Normalize confidence: Whisper avg_logprob is typically negative
            # Map roughly to 0-1 range
            if seg_confidence < 0:
                normalized_conf = min(1.0, max(0.0, 1.0 + seg_confidence))
            else:
                normalized_conf = min(1.0, seg_confidence)

            for i, kw_lower in enumerate(keywords_lower):
                if kw_lower in seg_text:
                    results.append(
                        {
                            "keyword": keywords[i],
                            "start_s": round(seg_start, 3),
                            "end_s": round(seg_end, 3),
                            "confidence": round(normalized_conf, 4),
                        }
                    )

        return results

    def create_wake_word_detector(
        self,
        wake_word: str,
    ) -> Callable[[np.ndarray, int], bool]:
        """Create a callable wake word detector.

        V1 implementation: energy-based trigger + STT verification.
        Detects energy spike, transcribes short window, checks for wake word.

        Args:
            wake_word: The word/phrase to detect.

        Returns:
            A callable that takes (audio_chunk, sr) and returns bool.
        """
        wake_lower = wake_word.lower()
        stt = self._stt

        import asyncio

        def detect(audio_chunk: np.ndarray, sr: int) -> bool:
            """Check if wake word is present in audio chunk."""
            # Step 1: Energy-based trigger — skip if too quiet
            rms = float(np.sqrt(np.mean(audio_chunk**2)))
            if rms < 1e-4:
                return False

            # Step 2: Transcribe and check for wake word
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context — create a new task
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            asyncio.run, stt.transcribe(audio_chunk, sr)
                        ).result(timeout=10)
                else:
                    result = asyncio.run(stt.transcribe(audio_chunk, sr))
            except Exception:
                # If transcription fails, fall back to energy-only
                return False

            text = result.get("text", "").lower()
            return wake_lower in text

        return detect
