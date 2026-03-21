"""Spectral analysis service: STFT, MEL, MFCC, and waveform statistics."""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np


class SpectralAnalyzer:
    """Compute spectral features from audio signals."""

    # ------------------------------------------------------------------
    # STFT
    # ------------------------------------------------------------------
    def compute_stft(
        self,
        audio: np.ndarray,
        sr: int,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """Short-Time Fourier Transform.

        Returns complex spectrogram, magnitude, phase, frequency and time axes.
        """
        stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length, window=window)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        times = librosa.frames_to_time(
            np.arange(stft.shape[1]), sr=sr, hop_length=hop_length
        )
        return {
            "spectrogram": stft,
            "magnitude": magnitude,
            "phase": phase,
            "freqs": freqs,
            "times": times,
        }

    # ------------------------------------------------------------------
    # MEL spectrogram
    # ------------------------------------------------------------------
    def compute_mel_spectrogram(
        self,
        audio: np.ndarray,
        sr: int,
        n_mels: int = 128,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> dict[str, np.ndarray]:
        """Mel-scaled spectrogram converted to dB."""
        mel = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop_length,
            window=window,
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_freqs = librosa.mel_frequencies(n_mels=n_mels, fmax=sr / 2)
        return {"mel_spectrogram": mel_db, "mel_freqs": mel_freqs}

    # ------------------------------------------------------------------
    # MFCC
    # ------------------------------------------------------------------
    def compute_mfcc(
        self,
        audio: np.ndarray,
        sr: int,
        n_mfcc: int = 13,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> dict[str, np.ndarray]:
        """Mel-frequency cepstral coefficients with first and second deltas."""
        mfcc = librosa.feature.mfcc(
            y=audio, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length
        )
        delta = librosa.feature.delta(mfcc)
        delta2 = librosa.feature.delta(mfcc, order=2)
        return {"mfcc": mfcc, "delta": delta, "delta2": delta2}

    # ------------------------------------------------------------------
    # Power spectrogram
    # ------------------------------------------------------------------
    def compute_power_spectrogram(
        self,
        audio: np.ndarray,
        sr: int,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> dict[str, np.ndarray]:
        """Power spectrogram (magnitude squared)."""
        stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
        power_spec = np.abs(stft) ** 2
        return {"power_spec": power_spec}

    # ------------------------------------------------------------------
    # Waveform statistics
    # ------------------------------------------------------------------
    def compute_waveform_stats(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict[str, Any]:
        """Basic waveform statistics."""
        rms = float(np.sqrt(np.mean(audio**2)))
        peak = float(np.max(np.abs(audio)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
        duration = float(len(audio) / sr)
        is_silent = rms < 1e-6
        return {
            "duration_s": duration,
            "sample_rate": sr,
            "samples": len(audio),
            "rms": rms,
            "peak_amplitude": peak,
            "zero_crossing_rate": zcr,
            "is_silent": is_silent,
        }

    # ------------------------------------------------------------------
    # All features
    # ------------------------------------------------------------------
    def extract_all_features(
        self,
        audio: np.ndarray,
        sr: int,
        config: dict | None = None,
    ) -> dict[str, Any]:
        """Run every feature extractor and return a combined dict."""
        cfg = config or {}
        n_fft = cfg.get("n_fft", 2048)
        hop_length = cfg.get("hop_length", 512)
        n_mels = cfg.get("n_mels", 128)
        n_mfcc = cfg.get("n_mfcc", 13)
        window = cfg.get("window", "hann")

        stft = self.compute_stft(audio, sr, n_fft=n_fft, hop_length=hop_length, window=window)
        mel = self.compute_mel_spectrogram(
            audio, sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop_length, window=window,
        )
        mfcc = self.compute_mfcc(
            audio, sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length
        )
        power = self.compute_power_spectrogram(
            audio, sr, n_fft=n_fft, hop_length=hop_length
        )
        waveform = self.compute_waveform_stats(audio, sr)

        return {
            "stft": stft,
            "mel": mel,
            "mfcc": mfcc,
            "power": power,
            "waveform": waveform,
        }
