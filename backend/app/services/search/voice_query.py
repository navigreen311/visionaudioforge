"""Voice query service — speech-to-text then text search."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class VoiceQueryService:
    """Process voice recordings: transcribe with Whisper, then search."""

    async def process_voice_query(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict[str, Any]:
        """Transcribe audio via STT and run a text search.

        Uses OpenAI Whisper if available, otherwise falls back to a stub
        transcript so the voice-to-search pipeline can still be exercised.

        Args:
            audio: Audio waveform as float32 numpy array.
            sr: Sample rate in Hz.

        Returns:
            Dict with ``transcript`` and ``search_results``.
        """
        transcript = self._transcribe(audio, sr)

        # Run text search with the transcript
        results: list[dict] = []
        if transcript:
            try:
                from app.services.search.embeddings import EmbeddingService
                from app.services.search.faiss_index import FAISSIndexService
                from app.services.search.search_service import CrossModalSearchService

                embedding_svc = EmbeddingService()
                index_svc = FAISSIndexService(dimension=512)
                index_svc.create_index("flat")
                search_svc = CrossModalSearchService(
                    embedding_svc=embedding_svc,
                    index_svc=index_svc,
                    db_session=None,
                )
                results = await search_svc.search_by_text(query=transcript, k=10)
            except Exception:
                logger.exception("Voice query search failed")

        return {
            "transcript": transcript,
            "search_results": results,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _transcribe(audio: np.ndarray, sr: int) -> str:
        """Transcribe audio using Whisper or return a stub transcript."""
        try:
            import whisper

            model = whisper.load_model("base")
            # Whisper expects float32 mono at 16 kHz
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            if sr != 16000:
                # Simple resampling via linear interpolation
                duration = len(audio) / sr
                n_samples = int(duration * 16000)
                indices = np.linspace(0, len(audio) - 1, n_samples)
                audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
            result = model.transcribe(audio)
            transcript = result.get("text", "").strip()
            logger.info("Whisper transcription: %r", transcript)
            return transcript
        except ImportError:
            logger.warning("Whisper not available — using stub transcript")
            return "voice query placeholder"
        except Exception:
            logger.exception("Whisper transcription failed — using stub")
            return "voice query placeholder"
