"""Audio embedding service: generate fixed-size vector representations of audio."""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np


class AudioEmbeddingService:
    """Generate 512-dimensional audio embeddings using handcrafted features."""

    EMBEDDING_DIM = 512

    # ------------------------------------------------------------------
    # Embedding methods
    # ------------------------------------------------------------------
    def embed_audio(
        self, audio: np.ndarray, sr: int, model: str = "mfcc_stats"
    ) -> np.ndarray:
        """Produce a 512-dim embedding for a single audio clip.

        Supported models:
        - ``'mfcc_stats'``: 40 MFCCs × 4 stats (mean/std/min/max) = 160 features, zero-padded.
        - ``'spectral'``: spectral centroid, bandwidth, rolloff, contrast, flatness stats, zero-padded.
        """
        if model == "mfcc_stats":
            return self._embed_mfcc_stats(audio, sr)
        elif model == "spectral":
            return self._embed_spectral(audio, sr)
        else:
            raise ValueError(f"Unknown embedding model: {model!r}. Use 'mfcc_stats' or 'spectral'.")

    def _embed_mfcc_stats(self, audio: np.ndarray, sr: int) -> np.ndarray:
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)  # (40, T)
        stats = np.concatenate([
            np.mean(mfccs, axis=1),
            np.std(mfccs, axis=1),
            np.min(mfccs, axis=1),
            np.max(mfccs, axis=1),
        ])  # 160 features
        embedding = np.zeros(self.EMBEDDING_DIM, dtype=np.float64)
        embedding[: len(stats)] = stats
        return embedding

    def _embed_spectral(self, audio: np.ndarray, sr: int) -> np.ndarray:
        features: list[float] = []

        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        features.extend([float(np.mean(centroid)), float(np.std(centroid))])

        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
        features.extend([float(np.mean(bandwidth)), float(np.std(bandwidth))])

        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        features.extend([float(np.mean(rolloff)), float(np.std(rolloff))])

        # Spectral contrast (7 bands by default)
        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
        features.extend(np.mean(contrast, axis=1).tolist())
        features.extend(np.std(contrast, axis=1).tolist())

        # Spectral flatness
        flatness = librosa.feature.spectral_flatness(y=audio)[0]
        features.extend([float(np.mean(flatness)), float(np.std(flatness))])

        embedding = np.zeros(self.EMBEDDING_DIM, dtype=np.float64)
        arr = np.array(features)
        embedding[: len(arr)] = arr
        return embedding

    # ------------------------------------------------------------------
    # Batch & similarity
    # ------------------------------------------------------------------
    def embed_audio_batch(
        self, audio_list: list[tuple[np.ndarray, int]], sr: int | None = None, model: str = "mfcc_stats"
    ) -> np.ndarray:
        """Embed a batch of audio clips. Returns shape (N, 512).

        Each element of *audio_list* is either an ``np.ndarray`` (uses *sr*)
        or a ``(audio, sample_rate)`` tuple.
        """
        embeddings = []
        for item in audio_list:
            if isinstance(item, tuple):
                a, s = item
            else:
                a, s = item, sr
            embeddings.append(self.embed_audio(a, s, model=model))
        return np.stack(embeddings)

    def compute_audio_similarity(
        self, audio1: np.ndarray, audio2: np.ndarray, sr: int
    ) -> float:
        """Compute cosine similarity between two audio clips' embeddings."""
        e1 = self.embed_audio(audio1, sr)
        e2 = self.embed_audio(audio2, sr)
        dot = float(np.dot(e1, e2))
        n1 = float(np.linalg.norm(e1))
        n2 = float(np.linalg.norm(e2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return round(dot / (n1 * n2), 6)
