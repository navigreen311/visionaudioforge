"""Voice Activity Detection using energy-based analysis."""

from __future__ import annotations

import numpy as np


class VoiceActivityDetector:
    """Detect speech regions in audio using frame-level RMS energy."""

    def detect(
        self,
        audio: np.ndarray,
        sr: int,
        frame_duration_ms: int = 30,
        energy_threshold: float | None = None,
    ) -> list[dict]:
        """Classify each frame as speech or non-speech.

        Returns a list of dicts with keys: start_s, end_s, is_speech, energy_db.
        """
        frame_len = int(sr * frame_duration_ms / 1000)
        if frame_len == 0:
            return []

        n_frames = len(audio) // frame_len
        if n_frames == 0:
            return []

        # Compute RMS energy per frame
        energies = np.array(
            [
                np.sqrt(np.mean(audio[i * frame_len : (i + 1) * frame_len] ** 2))
                for i in range(n_frames)
            ]
        )

        # Auto-threshold: half of mean energy (floor at a small absolute value
        # so pure silence is never classified as speech).
        if energy_threshold is None:
            mean_energy = np.mean(energies)
            energy_threshold = max(mean_energy * 0.5, 1e-6)

        results: list[dict] = []
        for i in range(n_frames):
            rms = energies[i]
            energy_db = 20.0 * np.log10(rms + 1e-10)
            start_s = i * frame_duration_ms / 1000.0
            end_s = (i + 1) * frame_duration_ms / 1000.0
            results.append(
                {
                    "start_s": round(start_s, 4),
                    "end_s": round(end_s, 4),
                    "is_speech": bool(rms >= energy_threshold),
                    "energy_db": round(float(energy_db), 2),
                }
            )

        return results

    def get_speech_segments(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> list[dict]:
        """Return merged consecutive speech regions.

        Returns list of dicts with keys: start_s, end_s, duration_s.
        """
        frames = self.detect(audio, sr)
        segments: list[dict] = []
        current_start: float | None = None

        for f in frames:
            if f["is_speech"]:
                if current_start is None:
                    current_start = f["start_s"]
            else:
                if current_start is not None:
                    end = f["start_s"]
                    segments.append(
                        {
                            "start_s": current_start,
                            "end_s": end,
                            "duration_s": round(end - current_start, 4),
                        }
                    )
                    current_start = None

        # Close trailing segment
        if current_start is not None and frames:
            end = frames[-1]["end_s"]
            segments.append(
                {
                    "start_s": current_start,
                    "end_s": end,
                    "duration_s": round(end - current_start, 4),
                }
            )

        return segments

    def get_speech_ratio(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> float:
        """Return the fraction of audio classified as speech (0.0 – 1.0)."""
        frames = self.detect(audio, sr)
        if not frames:
            return 0.0
        speech_count = sum(1 for f in frames if f["is_speech"])
        return speech_count / len(frames)
