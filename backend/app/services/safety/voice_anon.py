"""Voice anonymization service — pitch shifting, formant modulation, noise masking."""

from __future__ import annotations

import numpy as np


class VoiceAnonymizer:
    """Anonymize voice audio to prevent speaker identification."""

    # ------------------------------------------------------------------
    # Core anonymization
    # ------------------------------------------------------------------

    def anonymize(
        self, audio: np.ndarray, sr: int, method: str = "pitch"
    ) -> np.ndarray:
        """Anonymize an entire audio signal.

        Parameters
        ----------
        audio : 1-D float array
        sr : sample rate
        method : 'pitch' | 'formant' | 'noise_mask'
        """
        if method == "pitch":
            return self._pitch_shift(audio, sr)
        elif method == "formant":
            return self._formant_shift(audio, sr)
        elif method == "noise_mask":
            return self._noise_mask(audio, sr)
        else:
            raise ValueError(f"Unknown anonymization method: {method}")

    def anonymize_segments(
        self,
        audio: np.ndarray,
        sr: int,
        segments: list[dict],
        method: str = "pitch",
    ) -> np.ndarray:
        """Anonymize only specified speech segments (from VAD).

        Each segment: ``{"start": float_seconds, "end": float_seconds}``.
        Non-speech regions are left untouched.
        """
        result = audio.copy()
        for seg in segments:
            start_sample = int(seg["start"] * sr)
            end_sample = int(seg["end"] * sr)
            start_sample = max(0, start_sample)
            end_sample = min(len(audio), end_sample)
            if start_sample >= end_sample:
                continue
            chunk = audio[start_sample:end_sample]
            result[start_sample:end_sample] = self.anonymize(chunk, sr, method)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pitch_shift(audio: np.ndarray, sr: int) -> np.ndarray:
        """Shift pitch by +5 or -5 semitones via frequency-domain scaling."""
        rng = np.random.default_rng()
        direction = rng.choice([-1, 1])
        semitones = 5 * direction
        factor = 2.0 ** (semitones / 12.0)

        n = len(audio)
        # Shift in the frequency domain: scale frequency bins
        spectrum = np.fft.rfft(audio)
        n_bins = len(spectrum)
        shifted_spectrum = np.zeros_like(spectrum)

        for i in range(n_bins):
            new_bin = int(round(i * factor))
            if 0 <= new_bin < n_bins:
                shifted_spectrum[new_bin] += spectrum[i]

        result = np.fft.irfft(shifted_spectrum, n=n)
        return result.astype(audio.dtype)

    @staticmethod
    def _formant_shift(audio: np.ndarray, sr: int) -> np.ndarray:
        """Pitch shift + robotic modulation (low-frequency sine multiplication)."""
        # First apply pitch shift
        shifted = VoiceAnonymizer._pitch_shift(audio, sr)
        # Multiply with a low-frequency sine for robotic effect
        t = np.arange(len(shifted)) / sr
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 30 * t)  # 30 Hz modulation
        return (shifted * modulation).astype(audio.dtype)

    @staticmethod
    def _noise_mask(audio: np.ndarray, sr: int) -> np.ndarray:
        """Add pink noise at SNR = 5 dB to mask voice characteristics."""
        rng = np.random.default_rng()
        n = len(audio)

        # Generate approximate pink noise (1/f) via filtering white noise
        white = rng.standard_normal(n)
        # Simple 1/f approximation: apply cumulative filter
        fft = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        freqs[0] = 1.0  # avoid division by zero
        fft /= np.sqrt(freqs)
        pink = np.fft.irfft(fft, n=n)

        # Scale pink noise to achieve target SNR of 5 dB
        signal_power = np.mean(audio ** 2) + 1e-10
        snr_linear = 10.0 ** (5.0 / 10.0)
        noise_power = signal_power / snr_linear
        current_noise_power = np.mean(pink ** 2) + 1e-10
        pink *= np.sqrt(noise_power / current_noise_power)

        return (audio + pink).astype(audio.dtype)
