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
    # Spectral masking on a waveform
    # ------------------------------------------------------------------
    @staticmethod
    def spec_mask(
        audio: np.ndarray,
        sr: int,
        axis: str = "frequency",
        num_masks: int = 1,
        mask_size_pct: float = 10.0,
        n_fft: int = 2048,
    ) -> np.ndarray:
        """SpecAugment masking applied to a waveform, returning a waveform.

        :meth:`frequency_mask` and :meth:`time_mask` take a spectrogram and give
        one back, which is what a training pipeline wants. The augmentation
        endpoint takes audio in and must give audio back, so it cannot call them
        directly - and that is why "freq_mask" and "time_mask" were offered by
        the console and rejected by the server. This bridges the two: STFT, mask
        the requested axis, inverse STFT, trimmed to the original length.

        Args:
            audio: Input waveform.
            sr: Sample rate.
            axis: ``"frequency"`` or ``"time"``.
            num_masks: Number of bands to zero.
            mask_size_pct: Width of each band as a percentage of that axis,
                clamped to [0, 100].
            n_fft: FFT size for the round trip.

        Returns:
            Masked waveform, same length as *audio*.
        """
        if axis not in ("frequency", "time"):
            raise ValueError(f"Unknown mask axis: {axis!r}")

        n_fft = min(int(n_fft), max(16, len(audio)))
        stft = librosa.stft(audio, n_fft=n_fft)
        pct = float(np.clip(mask_size_pct, 0.0, 100.0)) / 100.0

        spec = np.abs(stft)
        phase = np.exp(1j * np.angle(stft))
        extent = spec.shape[0] if axis == "frequency" else spec.shape[1]
        width = max(1, int(round(extent * pct)))

        masked = (
            AudioAugmenter.frequency_mask(spec, num_masks=num_masks, mask_width=width)
            if axis == "frequency"
            else AudioAugmenter.time_mask(spec, num_masks=num_masks, mask_width=width)
        )

        out = librosa.istft(masked * phase, n_fft=n_fft, length=len(audio))
        return np.asarray(out, dtype=audio.dtype)

    # ------------------------------------------------------------------
    # Request vocabulary
    # ------------------------------------------------------------------
    #
    # The console and this service were written against different names, and
    # nothing checked that they agreed. `AugmentationStudio` sent "white_noise",
    # "pink_noise", "time_stretch", "pitch_shift", "time_shift" and
    # "frequency_mask" - not one of which this file accepted, so every request
    # from that panel raised ValueError and surfaced as a 500.
    # `AugmentationBuilder` sent "freq_mask"/"time_mask" (also unknown) and sent
    # pitch as `semitones` when the method takes `n_steps`, which raised
    # TypeError. Three of its six controls were dead and three worked.
    #
    # Rather than pick one side and break the other, every name either panel
    # emits is accepted and canonicalised here. `tests/test_console_api_contract.py`
    # reads the console source and fails if it grows a name this table lacks, so
    # the two cannot drift apart again in silence.
    _ALIASES: dict[str, tuple[str, dict[str, Any]]] = {
        "noise": ("noise", {}),
        "white_noise": ("noise", {"noise_type": "white"}),
        "pink_noise": ("noise", {"noise_type": "pink"}),
        "brown_noise": ("noise", {"noise_type": "brown"}),
        "stretch": ("stretch", {}),
        "time_stretch": ("stretch", {}),
        "pitch": ("pitch", {}),
        "pitch_shift": ("pitch", {}),
        "shift": ("shift", {}),
        "time_shift": ("shift", {}),
        "freq_mask": ("spec_mask", {"axis": "frequency"}),
        "frequency_mask": ("spec_mask", {"axis": "frequency"}),
        "time_mask": ("spec_mask", {"axis": "time"}),
    }

    @staticmethod
    def _normalise_params(
        op: str, params: dict[str, Any], audio: np.ndarray, sr: int
    ) -> dict[str, Any]:
        """Translate a step's params into the canonical method's keywords.

        Two of these need the audio to resolve, which is why normalisation
        happens per-step at apply time rather than once up front: a shift given
        as a percentage of the clip only becomes milliseconds when the clip is
        known.
        """
        out = dict(params)

        if op == "noise":
            # The studio's pink-noise control is an amplitude in (0, 1]; the
            # method takes a target SNR. A unit-amplitude noise floor is 0 dB
            # SNR and every halving is ~6 dB quieter, so -20*log10(a) is the
            # conversion. Values outside the range are clamped rather than
            # rejected, because a slider at 0 should mean "no noise", not a 500.
            if "amplitude" in out:
                amplitude = float(np.clip(out.pop("amplitude"), 1e-4, 1.0))
                out.setdefault("snr_db", float(-20.0 * np.log10(amplitude)))
            if "snr" in out:
                out.setdefault("snr_db", out.pop("snr"))

        elif op == "pitch":
            # The console has always called these semitones, which is also what
            # the method's docstring calls them; only the keyword differed.
            for alias in ("semitones", "steps"):
                if alias in out:
                    out.setdefault("n_steps", out.pop(alias))

        elif op == "shift":
            if "shift_pct" in out:
                duration_ms = 1000.0 * len(audio) / float(sr)
                pct = float(out.pop("shift_pct"))
                out.setdefault("shift_ms", duration_ms * pct / 100.0)
            if "shift_s" in out:
                out.setdefault("shift_ms", float(out.pop("shift_s")) * 1000.0)

        elif op == "spec_mask":
            # `mask_size` from the builder is a count of bins; `mask_size_pct`
            # from the studio is a share of the axis. Bins cannot be converted
            # without the STFT shape, so they are carried as a width and
            # resolved against it below.
            if "mask_size" in out:
                out.setdefault("mask_width_bins", out.pop("mask_size"))
            if "mask_width" in out:
                out.setdefault("mask_width_bins", out.pop("mask_width"))

        return out

    @classmethod
    def canonical_step(cls, step_type: str) -> str:
        """The method a request name resolves to, or raise listing every name."""
        entry = cls._ALIASES.get(step_type)
        if entry is None:
            known = ", ".join(sorted(cls._ALIASES))
            raise ValueError(
                f"Unknown augmentation type: {step_type!r}. Known types: {known}"
            )
        return entry[0]

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
        - ``type``: any name in :attr:`_ALIASES`
        - ``probability``: float in [0, 1] (default 1.0)
        - ``params``: dict forwarded to the method, after normalisation

        Returns:
            A tuple of (augmented_audio, applied_augmentations). The report names
            the canonical operation and the params actually used alongside the
            name that was requested, so a caller can see what really ran.
        """
        _dispatch = {
            "noise": self.add_noise,
            "stretch": self.time_stretch,
            "pitch": self.pitch_shift,
            "shift": self.time_shift,
            "spec_mask": self.spec_mask,
        }

        result = audio.copy()
        applied: list[dict[str, Any]] = []

        for step in config:
            step_type = step["type"]
            probability = step.get("probability", 1.0)

            # Resolve before the probability gate. An unknown name is a caller
            # error whether or not this run happened to roll below the gate, and
            # a pipeline that fails only sometimes is worse than one that always
            # does.
            op, implied = self._ALIASES.get(step_type, (None, {}))
            if op is None:
                known = ", ".join(sorted(self._ALIASES))
                raise ValueError(
                    f"Unknown augmentation type: {step_type!r}. Known types: {known}"
                )

            if random.random() >= probability:
                continue

            params = {**implied, **step.get("params", {})}
            params = self._normalise_params(op, params, result, sr)

            if op == "spec_mask":
                bins = params.pop("mask_width_bins", None)
                if bins is not None and "mask_size_pct" not in params:
                    n_fft = min(2048, max(16, len(result)))
                    if params.get("axis") == "frequency":
                        extent = n_fft // 2 + 1
                    else:
                        extent = max(1, 1 + len(result) // (n_fft // 4))
                    params["mask_size_pct"] = 100.0 * float(bins) / float(extent)

            try:
                result = _dispatch[op](result, sr, **params)
            except TypeError as exc:
                # The other half of the drift: a name that resolved but a keyword
                # that did not. Say which, rather than letting a bare TypeError
                # surface as an opaque 500.
                raise ValueError(
                    f"Bad params for augmentation {step_type!r} -> {op}: {exc}"
                ) from exc

            applied.append({"type": op, "requested": step_type, "params": params})

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
