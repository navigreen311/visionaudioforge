"""AV sync detection service: detect audio-video synchronisation offsets."""

from __future__ import annotations

from typing import Any

import numpy as np


class AVSyncDetector:
    """Detect audio/video synchronisation issues."""

    SYNC_THRESHOLD_MS = 100.0  # abs offset below this → considered synced

    # ------------------------------------------------------------------
    # Energy envelope helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _audio_energy_envelope(audio: np.ndarray, sr: int, fps: float) -> np.ndarray:
        """Compute per-frame audio energy aligned to video frame rate."""
        samples_per_frame = int(sr / fps)
        n_frames = len(audio) // samples_per_frame
        envelope = np.array(
            [
                np.sqrt(np.mean(audio[i * samples_per_frame : (i + 1) * samples_per_frame] ** 2))
                for i in range(n_frames)
            ]
        )
        return envelope

    @staticmethod
    def _video_brightness_changes(video_frames: list[np.ndarray]) -> np.ndarray:
        """Compute brightness difference between consecutive frames."""
        brightness = np.array([float(np.mean(f)) for f in video_frames])
        if len(brightness) < 2:
            return np.array([0.0])
        changes = np.abs(np.diff(brightness))
        return changes

    # ------------------------------------------------------------------
    # Sync offset detection
    # ------------------------------------------------------------------
    def detect_sync_offset(
        self,
        video_frames: list[np.ndarray],
        audio: np.ndarray,
        sr: int,
        fps: float,
    ) -> dict[str, Any]:
        """Detect AV sync offset via cross-correlation.

        Cross-correlates the audio energy envelope with video brightness
        changes to find the best alignment.

        Returns dict with *offset_ms*, *is_synced*, and *confidence*.
        """
        audio_env = self._audio_energy_envelope(audio, sr, fps)
        video_changes = self._video_brightness_changes(video_frames)

        # Align lengths
        min_len = min(len(audio_env), len(video_changes))
        if min_len < 2:
            return {"offset_ms": 0.0, "is_synced": True, "confidence": 0.0}

        a = audio_env[:min_len]
        v = video_changes[:min_len]

        # Normalise
        a = a - np.mean(a)
        v = v - np.mean(v)
        a_std = np.std(a)
        v_std = np.std(v)

        if a_std == 0 or v_std == 0:
            return {"offset_ms": 0.0, "is_synced": True, "confidence": 0.0}

        # Cross-correlation
        corr = np.correlate(a, v, mode="full")
        corr /= (a_std * v_std * min_len)

        peak_idx = int(np.argmax(np.abs(corr)))
        offset_frames = peak_idx - (min_len - 1)
        offset_ms = (offset_frames / fps) * 1000.0
        confidence = float(np.max(np.abs(corr)))

        return {
            "offset_ms": round(offset_ms, 2),
            "is_synced": abs(offset_ms) < self.SYNC_THRESHOLD_MS,
            "confidence": round(min(confidence, 1.0), 4),
        }

    # ------------------------------------------------------------------
    # Lip-sync stub
    # ------------------------------------------------------------------
    def check_lip_sync(
        self, face_frames: list, audio_segments: list
    ) -> dict[str, Any]:
        """Check lip-sync quality (stub — real implementation needs a specialised model).

        Returns a moderate score with an explanatory note.
        """
        return {
            "sync_score": 0.65,
            "verdict": "moderate",
            "note": "Real lip-sync analysis requires a specialised audio-visual model.",
        }
