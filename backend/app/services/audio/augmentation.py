"""Audio augmentation service for the Vision & Audio AI platform.

Provides noise injection, temporal modifications, pitch shifting,
and SpecAugment-style spectral masking for audio data augmentation.
"""

from __future__ import annotations

import random
from typing import Any

import librosa
import numpy as np


class AudioAugmenter:
    """Configurable audio augmentation pipeline.

    Supports white/pink/brown noise injection, time stretching,
    pitch shifting, time shifting, and SpecAugment masking.
    """

    # ------------------------------------------------------------------
    # Noise injection
    # ------------------------------------------------------------------
    @staticmethod
    def add_noise(
        audio: np.ndarray,
        sr: int,
        noise_type: str = "white",
        snr_db: float = 20.0,
    ) -> np.ndarray:
        """Add noise at a target signal-to-noise ratio.

        Args:
            audio: Input waveform (1-D float array).
            sr: Sample rate (unused for noise generation but kept for API consistency).
            noise_type: One of ``"white"``, ``"pink"``, ``"brown"``.
            snr_db: Desired SNR in decibels.

        Returns:
            Noisy waveform with the same length as *audio*.
        """
        n_samples = len(audio)

        if noise_type == "white":
            noise = np.random.randn(n_samples)
        elif noise_type == "pink":
            # 1/f spectrum via frequency-domain shaping
            freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
            freqs[0] = 1.0  # avoid division by zero
            spectrum = np.random.randn(len(freqs)) + 1j * np.random.randn(len(freqs))
            spectrum /= np.sqrt(freqs)
            noise = np.fft.irfft(spectrum, n=n_samples)
        elif noise_type == "brown":
            # Brownian / red noise: cumulative sum of white noise
            noise = np.cumsum(np.random.randn(n_samples))
        else:
            raise ValueError(f"Unknown noise_type: {noise_type!r}")

        # Scale noise to achieve target SNR
        signal_power = np.mean(audio ** 2)
        noise_power_target = signal_power / (10.0 ** (snr_db / 10.0))
        current_noise_power = np.mean(noise ** 2)
        if current_noise_power > 0:
            noise = noise * np.sqrt(noise_power_target / current_noise_power)

        return audio + noise

    # ------------------------------------------------------------------
    # Time stretch
    # ------------------------------------------------------------------
    @staticmethod
    def time_stretch(
        audio: np.ndarray,
        sr: int,
        rate: float = 1.0,
    ) -> np.ndarray:
        """Time-stretch *audio* by *rate* without changing pitch.

        Args:
            audio: Input waveform.
            sr: Sample rate.
            rate: Stretch factor (>1 faster / shorter, <1 slower / longer).
                  Clamped to [0.5, 2.0].

        Returns:
            Time-stretched waveform.
        """
        rate = float(np.clip(rate, 0.5, 2.0))
        return librosa.effects.time_stretch(audio, rate=rate)

    # ------------------------------------------------------------------
    # Pitch shift
    # ------------------------------------------------------------------
    @staticmethod
    def pitch_shift(
        audio: np.ndarray,
        sr: int,
        n_steps: float = 0.0,
    ) -> np.ndarray:
        """Shift pitch by *n_steps* semitones.

        Args:
            audio: Input waveform.
            sr: Sample rate.
            n_steps: Number of semitones (positive = up). Clamped to [-12, 12].

        Returns:
            Pitch-shifted waveform (same length as input).
        """
        n_steps = float(np.clip(n_steps, -12, 12))
        return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)

    # ------------------------------------------------------------------
    # Time shift
    # ------------------------------------------------------------------
    @staticmethod
    def time_shift(
        audio: np.ndarray,
        sr: int,
        shift_ms: float = 0.0,
    ) -> np.ndarray:
        """Shift audio in time by *shift_ms* milliseconds.

        Positive values pad the start with zeros (delay).
        Negative values trim the start.

        Args:
            audio: Input waveform.
            sr: Sample rate.
            shift_ms: Shift amount in milliseconds.

        Returns:
            Time-shifted waveform with the same length as *audio*.
        """
        shift_samples = int(sr * shift_ms / 1000.0)
        result = np.roll(audio, shift_samples)
        if shift_samples > 0:
            result[:shift_samples] = 0.0
        elif shift_samples < 0:
            result[shift_samples:] = 0.0
        return result

    # ------------------------------------------------------------------
    # SpecAugment: frequency mask
    # ------------------------------------------------------------------
    @staticmethod
    def frequency_mask(
        spectrogram: np.ndarray,
        num_masks: int = 1,
        mask_width: int = 10,
    ) -> np.ndarray:
        """Apply SpecAugment frequency masking.

        Randomly zeroes out horizontal bands (frequency bins) in a spectrogram.

        Args:
            spectrogram: 2-D array of shape ``(n_freq, n_time)``.
            num_masks: Number of masks to apply.
            mask_width: Maximum width of each mask in frequency bins.

        Returns:
            Masked spectrogram (copy).
        """
        spec = spectrogram.copy()
        n_freq = spec.shape[0]
        for _ in range(num_masks):
            f_start = random.randint(0, max(0, n_freq - mask_width))
            f_end = min(f_start + mask_width, n_freq)
            spec[f_start:f_end, :] = 0.0
        return spec

    # ------------------------------------------------------------------
    # SpecAugment: time mask
    # ------------------------------------------------------------------
    @staticmethod
    def time_mask(
        spectrogram: np.ndarray,
        num_masks: int = 1,
        mask_width: int = 10,
    ) -> np.ndarray:
        """Apply SpecAugment time masking.

        Randomly zeroes out vertical bands (time steps) in a spectrogram.

        Args:
            spectrogram: 2-D array of shape ``(n_freq, n_time)``.
            num_masks: Number of masks to apply.
            mask_width: Maximum width of each mask in time steps.

        Returns:
            Masked spectrogram (copy).
        """
        spec = spectrogram.copy()
        n_time = spec.shape[1]
        for _ in range(num_masks):
            t_start = random.randint(0, max(0, n_time - mask_width))
            t_end = min(t_start + mask_width, n_time)
            spec[:, t_start:t_end] = 0.0
        return spec

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def apply_pipeline(
        self,
        audio: np.ndarray,
        sr: int,
        config: list[dict[str, Any]],
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """Apply a sequence of augmentation steps with probabilistic gating.

        Each element of *config* is a dict with keys:
        - ``type``: one of ``"noise"``, ``"stretch"``, ``"pitch"``, ``"shift"``
        - ``probability``: float in [0, 1] (default 1.0)
        - ``params``: dict of keyword arguments forwarded to the method

        Returns:
            A tuple of (augmented_audio, applied_augmentations).
        """
        _dispatch = {
            "noise": self.add_noise,
            "stretch": self.time_stretch,
            "pitch": self.pitch_shift,
            "shift": self.time_shift,
        }

        result = audio.copy()
        applied: list[dict[str, Any]] = []

        for step in config:
            aug_type = step["type"]
            probability = step.get("probability", 1.0)
            params = step.get("params", {})

            if random.random() < probability:
                fn = _dispatch.get(aug_type)
                if fn is None:
                    raise ValueError(f"Unknown augmentation type: {aug_type!r}")
                result = fn(result, sr, **params)
                applied.append({"type": aug_type, "params": params})

        return result, applied

    # ------------------------------------------------------------------
    # Batch augmentation
    # ------------------------------------------------------------------
    def augment_batch(
        self,
        audio_list: list[np.ndarray],
        sr: int,
        config: list[dict[str, Any]],
        num_versions: int = 3,
    ) -> list[list[np.ndarray]]:
        """Generate multiple augmented versions for each audio clip.

        Args:
            audio_list: List of input waveforms.
            sr: Sample rate.
            config: Pipeline configuration (see :meth:`apply_pipeline`).
            num_versions: Number of augmented copies per input.

        Returns:
            A list of lists — one inner list of *num_versions* arrays per input.
        """
        results: list[list[np.ndarray]] = []
        for audio in audio_list:
            versions: list[np.ndarray] = []
            for _ in range(num_versions):
                augmented, _ = self.apply_pipeline(audio, sr, config)
                versions.append(augmented)
            results.append(versions)
        return results
