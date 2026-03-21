"""Unified audio service — facade over spectral analysis with configurable parameters.

Centralises configuration for n_fft, hop_length, window, and n_mfcc so that
callers can set them once and have all downstream computations respect the same
values.
"""

from __future__ import annotations

from typing import Any, Literal

import librosa
import numpy as np

from app.services.audio.spectral import SpectralAnalyzer

# Allowed parameter values (enforced at the service boundary).
VALID_N_FFT = {512, 1024, 2048, 4096}
VALID_HOP_LENGTH = {128, 256, 512}
VALID_WINDOW = {"hann", "hamming", "blackman"}


class AudioService:
    """High-level audio analysis service with validated spectral parameters."""

    def __init__(self) -> None:
        self._analyzer = SpectralAnalyzer()

    # ------------------------------------------------------------------
    # Parameter validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_n_fft(n_fft: int) -> int:
        if n_fft not in VALID_N_FFT:
            raise ValueError(
                f"n_fft must be one of {sorted(VALID_N_FFT)}, got {n_fft}"
            )
        return n_fft

    @staticmethod
    def _validate_hop_length(hop_length: int) -> int:
        if hop_length not in VALID_HOP_LENGTH:
            raise ValueError(
                f"hop_length must be one of {sorted(VALID_HOP_LENGTH)}, got {hop_length}"
            )
        return hop_length

    @staticmethod
    def _validate_window(window: str) -> str:
        if window not in VALID_WINDOW:
            raise ValueError(
                f"window must be one of {sorted(VALID_WINDOW)}, got {window!r}"
            )
        return window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_stft(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """STFT with validated parameters."""
        return self._analyzer.compute_stft(
            audio,
            sr,
            n_fft=self._validate_n_fft(n_fft),
            hop_length=self._validate_hop_length(hop_length),
            window=self._validate_window(window),
        )

    def compute_mel_spectrogram(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        n_mels: int = 128,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """Mel spectrogram with validated parameters."""
        return self._analyzer.compute_mel_spectrogram(
            audio,
            sr,
            n_mels=n_mels,
            n_fft=self._validate_n_fft(n_fft),
            hop_length=self._validate_hop_length(hop_length),
            window=self._validate_window(window),
        )

    def compute_mfcc(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        n_mfcc: int = 13,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """MFCC with validated parameters."""
        return self._analyzer.compute_mfcc(
            audio,
            sr,
            n_mfcc=n_mfcc,
            n_fft=self._validate_n_fft(n_fft),
            hop_length=self._validate_hop_length(hop_length),
            window=self._validate_window(window),
        )

    def compute_power_spectrogram(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """Power spectrogram with validated parameters."""
        return self._analyzer.compute_power_spectrogram(
            audio,
            sr,
            n_fft=self._validate_n_fft(n_fft),
            hop_length=self._validate_hop_length(hop_length),
            window=self._validate_window(window),
        )

    def compute_waveform_stats(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict[str, Any]:
        """Waveform statistics (delegates directly)."""
        return self._analyzer.compute_waveform_stats(audio, sr)

    def extract_all_features(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
        n_mels: int = 128,
        n_mfcc: int = 13,
    ) -> dict[str, Any]:
        """Run all feature extractors with validated parameters."""
        config = {
            "n_fft": self._validate_n_fft(n_fft),
            "hop_length": self._validate_hop_length(hop_length),
            "window": self._validate_window(window),
            "n_mels": n_mels,
            "n_mfcc": n_mfcc,
        }
        return self._analyzer.extract_all_features(audio, sr, config=config)
