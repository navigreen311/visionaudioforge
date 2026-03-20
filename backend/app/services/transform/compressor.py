"""Dynamic range compressor and limiter.

Frame-by-frame compression with attack/release smoothing.
"""

from __future__ import annotations

import numpy as np

_PRESETS: dict[str, dict] = {
    "gentle": {"threshold_db": -20, "ratio": 2.0, "attack_ms": 10, "release_ms": 100, "makeup_gain_db": 0},
    "moderate": {"threshold_db": -15, "ratio": 4.0, "attack_ms": 5, "release_ms": 50, "makeup_gain_db": 0},
    "aggressive": {"threshold_db": -10, "ratio": 8.0, "attack_ms": 2, "release_ms": 30, "makeup_gain_db": 0},
    "broadcast": {"threshold_db": -12, "ratio": 6.0, "attack_ms": 5, "release_ms": 50, "makeup_gain_db": 3},
}


class DynamicCompressor:
    """Dynamic range compressor with attack/release envelope."""

    def compress(
        self,
        audio: np.ndarray,
        sr: int,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
        makeup_gain_db: float = 0.0,
    ) -> np.ndarray:
        """Apply dynamic range compression frame-by-frame.

        For each sample:
        1. Compute level in dB
        2. If level > threshold, compute gain reduction
        3. Apply attack/release smoothing
        4. Apply makeup gain
        """
        audio = audio.astype(np.float64)

        # Compute per-sample level in dB
        abs_audio = np.abs(audio)
        level_db = 20 * np.log10(abs_audio + 1e-30)

        # Compute gain reduction
        gain_reduction_db = np.zeros_like(level_db)
        above_threshold = level_db > threshold_db
        gain_reduction_db[above_threshold] = (
            (level_db[above_threshold] - threshold_db) * (1.0 - 1.0 / ratio)
        )

        # Attack / release smoothing
        attack_coeff = np.exp(-1.0 / (attack_ms * 0.001 * sr)) if attack_ms > 0 else 0.0
        release_coeff = np.exp(-1.0 / (release_ms * 0.001 * sr)) if release_ms > 0 else 0.0

        smoothed = np.zeros_like(gain_reduction_db)
        prev = 0.0
        for i in range(len(gain_reduction_db)):
            target = gain_reduction_db[i]
            if target > prev:
                # Attack (increasing gain reduction)
                prev = attack_coeff * prev + (1 - attack_coeff) * target
            else:
                # Release (decreasing gain reduction)
                prev = release_coeff * prev + (1 - release_coeff) * target
            smoothed[i] = prev

        # Apply gain reduction
        gain_linear = 10 ** (-smoothed / 20.0)
        output = audio * gain_linear

        # Apply makeup gain
        if makeup_gain_db != 0.0:
            makeup_linear = 10 ** (makeup_gain_db / 20.0)
            output = output * makeup_linear

        return np.clip(output, -1.0, 1.0).astype(np.float32)

    def apply_limiter(
        self,
        audio: np.ndarray,
        sr: int,
        ceiling_db: float = -1.0,
    ) -> np.ndarray:
        """Hard limiter — clip any sample exceeding ceiling."""
        ceiling_linear = 10 ** (ceiling_db / 20.0)
        return np.clip(audio, -ceiling_linear, ceiling_linear).astype(np.float32)

    def presets(self) -> dict:
        """Return available compressor presets."""
        return dict(_PRESETS)
