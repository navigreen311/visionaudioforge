"""Dereverberation service — spectral subtraction approach.

Estimates reverb tail from late energy and applies spectral gating.
"""

from __future__ import annotations

import numpy as np


class Dereverberation:
    """Remove reverberation from audio using spectral subtraction."""

    def remove_reverb(
        self,
        audio: np.ndarray,
        sr: int,
        strength: float = 0.5,
    ) -> np.ndarray:
        """Remove reverb via spectral gating.

        1. Compute STFT
        2. Estimate noise floor from low-energy frames
        3. Apply spectral gating with strength parameter
        4. ISTFT back
        """
        strength = np.clip(strength, 0.0, 1.0)

        # STFT parameters
        n_fft = 2048
        hop_length = n_fft // 4
        window = np.hanning(n_fft)

        # Pad audio
        pad_len = n_fft - (len(audio) % hop_length)
        audio_padded = np.concatenate([audio, np.zeros(pad_len)])

        # Compute STFT
        n_frames = 1 + (len(audio_padded) - n_fft) // hop_length
        stft = np.zeros((n_fft // 2 + 1, n_frames), dtype=np.complex128)

        for i in range(n_frames):
            start = i * hop_length
            frame = audio_padded[start : start + n_fft] * window
            spectrum = np.fft.rfft(frame)
            stft[:, i] = spectrum

        magnitude = np.abs(stft)
        phase = np.angle(stft)

        # Estimate noise floor from lowest-energy frames (bottom 20%)
        frame_energy = np.sum(magnitude ** 2, axis=0)
        threshold_idx = max(1, int(0.2 * n_frames))
        sorted_indices = np.argsort(frame_energy)
        low_energy_frames = sorted_indices[:threshold_idx]
        noise_floor = np.mean(magnitude[:, low_energy_frames], axis=1, keepdims=True)

        # Spectral gating — subtract estimated reverb tail
        gain = np.maximum(magnitude - strength * noise_floor * 3.0, 0.0)
        # Wiener-like filter to avoid musical noise
        mask = gain / (magnitude + 1e-10)
        mask = np.clip(mask, 0.0, 1.0)

        # Smooth mask across time
        for i in range(1, n_frames):
            mask[:, i] = 0.7 * mask[:, i] + 0.3 * mask[:, i - 1]

        cleaned_stft = magnitude * mask * np.exp(1j * phase)

        # ISTFT via overlap-add
        output = np.zeros(len(audio_padded))
        window_sum = np.zeros(len(audio_padded))

        for i in range(n_frames):
            start = i * hop_length
            frame = np.fft.irfft(cleaned_stft[:, i]) * window
            output[start : start + n_fft] += frame
            window_sum[start : start + n_fft] += window ** 2

        # Normalize by window sum
        nonzero = window_sum > 1e-10
        output[nonzero] /= window_sum[nonzero]

        return output[: len(audio)].astype(np.float32)

    def estimate_rt60(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict:
        """Estimate RT60 from energy decay curve.

        Returns rt60_ms and room_size_estimate.
        """
        # Compute energy decay curve using Schroeder integration
        energy = audio.astype(np.float64) ** 2

        # Backward integration (Schroeder curve)
        decay = np.cumsum(energy[::-1])[::-1]
        decay = decay / (decay[0] + 1e-30)

        # Convert to dB
        decay_db = 10 * np.log10(decay + 1e-30)

        # Find time for -60 dB decay (or extrapolate from -20 dB)
        # Use -20 dB point and multiply by 3 for robustness
        target_db = -20.0
        below = np.where(decay_db < target_db)[0]

        if len(below) > 0:
            t20_samples = below[0]
            rt60_samples = t20_samples * 3  # Extrapolate to -60 dB
        else:
            # If decay never reaches -20 dB, estimate from total length
            rt60_samples = len(audio) // 2

        rt60_ms = float(rt60_samples / sr * 1000)

        # Room size estimation
        if rt60_ms < 300:
            room_size = "small"
        elif rt60_ms < 800:
            room_size = "medium"
        else:
            room_size = "large"

        return {
            "rt60_ms": round(rt60_ms, 1),
            "room_size_estimate": room_size,
        }
