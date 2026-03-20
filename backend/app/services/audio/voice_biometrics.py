"""Voice biometrics service: voiceprint extraction, comparison, and speaker identification."""

from __future__ import annotations

import hashlib
import uuid

import librosa
import numpy as np


class VoiceBiometrics:
    """Extract and compare voice biometric features (voiceprints)."""

    SIMILARITY_THRESHOLD = 0.7

    # ------------------------------------------------------------------
    # Voiceprint extraction
    # ------------------------------------------------------------------
    def extract_voiceprint(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Extract a 128-dimensional voiceprint vector from audio.

        The voiceprint is composed of:
        - 13 MFCCs averaged over time (13 dims)
        - Spectral centroid mean and std (2 dims)
        - Pitch (f0) mean and std (2 dims)
        - Zero-crossing rate mean and std (2 dims)
        Total raw features = 19, zero-padded and L2-normalised to 128 dims.
        """
        # MFCCs — 13 coefficients, averaged over time
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)  # (13,)

        # Spectral centroid stats
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        centroid_stats = np.array([np.mean(centroid), np.std(centroid)])

        # Pitch (f0) stats via pyin
        f0, voiced_flag, _ = librosa.pyin(
            audio, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
        )
        f0_valid = f0[~np.isnan(f0)] if np.any(~np.isnan(f0)) else np.array([0.0])
        pitch_stats = np.array([np.mean(f0_valid), np.std(f0_valid)])

        # Zero-crossing rate stats
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        zcr_stats = np.array([np.mean(zcr), np.std(zcr)])

        # Concatenate raw features
        raw = np.concatenate([mfcc_mean, centroid_stats, pitch_stats, zcr_stats])

        # Zero-pad to 128 dimensions
        voiceprint = np.zeros(128, dtype=np.float64)
        voiceprint[: len(raw)] = raw

        # L2-normalise
        norm = np.linalg.norm(voiceprint)
        if norm > 0:
            voiceprint /= norm

        return voiceprint

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    def compare_voiceprints(
        self, vp1: np.ndarray, vp2: np.ndarray
    ) -> dict:
        """Compare two voiceprints using cosine similarity.

        Returns dict with *similarity* (0–1) and *is_same_speaker* bool.
        """
        dot = float(np.dot(vp1, vp2))
        norm1 = float(np.linalg.norm(vp1))
        norm2 = float(np.linalg.norm(vp2))
        similarity = dot / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0.0
        # Clamp to [0, 1]
        similarity = max(0.0, min(1.0, similarity))
        return {
            "similarity": round(similarity, 6),
            "is_same_speaker": similarity >= self.SIMILARITY_THRESHOLD,
        }

    # ------------------------------------------------------------------
    # Speaker enrolment
    # ------------------------------------------------------------------
    def enroll_speaker(
        self, name: str, audio_samples: list[tuple[np.ndarray, int]]
    ) -> dict:
        """Enroll a speaker by averaging voiceprints from multiple samples.

        *audio_samples* is a list of ``(audio_array, sample_rate)`` tuples.
        """
        voiceprints = [self.extract_voiceprint(a, sr) for a, sr in audio_samples]
        avg_vp = np.mean(voiceprints, axis=0)
        # Re-normalise
        norm = np.linalg.norm(avg_vp)
        if norm > 0:
            avg_vp /= norm

        speaker_id = str(uuid.uuid4())
        return {
            "speaker_id": speaker_id,
            "voiceprint": avg_vp.tolist(),
            "samples_used": len(audio_samples),
        }

    # ------------------------------------------------------------------
    # Speaker identification
    # ------------------------------------------------------------------
    def identify_speaker(
        self, audio: np.ndarray, sr: int, enrolled_speakers: dict[str, np.ndarray]
    ) -> dict:
        """Identify the speaker in *audio* against enrolled voiceprints.

        *enrolled_speakers* maps speaker name → voiceprint (np.ndarray).
        Returns best match above threshold, or None.
        """
        query_vp = self.extract_voiceprint(audio, sr)

        all_scores: dict[str, float] = {}
        best_name: str | None = None
        best_score: float = -1.0

        for name, enrolled_vp in enrolled_speakers.items():
            result = self.compare_voiceprints(query_vp, np.asarray(enrolled_vp))
            score = result["similarity"]
            all_scores[name] = score
            if score > best_score:
                best_score = score
                best_name = name

        matched = best_name if best_score >= self.SIMILARITY_THRESHOLD else None
        return {
            "speaker": matched,
            "confidence": round(best_score, 6) if best_score >= 0 else 0.0,
            "all_scores": all_scores,
        }
