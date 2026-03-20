"""Audio Transform Service — denoise, silence removal, pitch, stretch, EQ, and chaining."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, stft, istft


class AudioTransformService:
    """Stateless collection of audio transform operations."""

    # ------------------------------------------------------------------
    # Denoise
    # ------------------------------------------------------------------
    def denoise(
        self,
        audio: np.ndarray,
        sr: int,
        method: str = "spectral_gating",
    ) -> np.ndarray:
        """Spectral-gating noise reduction.

        1. Compute STFT.
        2. Estimate noise profile from the quietest 10 % of frames.
        3. Subtract noise spectrum (floored at 0).
        4. Reconstruct with ISTFT.
        """
        if method != "spectral_gating":
            raise ValueError(f"Unsupported denoise method: {method}")

        nperseg = min(1024, len(audio))
        f, t, Zxx = stft(audio, fs=sr, nperseg=nperseg)

        magnitude = np.abs(Zxx)
        phase = np.angle(Zxx)

        # Frame energy → pick quietest 10 %
        frame_energy = np.sum(magnitude**2, axis=0)
        n_quiet = max(1, int(len(frame_energy) * 0.10))
        quiet_idx = np.argsort(frame_energy)[:n_quiet]
        noise_profile = np.mean(magnitude[:, quiet_idx], axis=1, keepdims=True)

        # Subtract and floor
        cleaned_mag = np.maximum(magnitude - noise_profile, 0.0)
        cleaned_stft = cleaned_mag * np.exp(1j * phase)

        _, reconstructed = istft(cleaned_stft, fs=sr, nperseg=nperseg)
        # Match original length
        reconstructed = _match_length(reconstructed, len(audio))
        return reconstructed.astype(audio.dtype)

    # ------------------------------------------------------------------
    # Remove silence
    # ------------------------------------------------------------------
    def remove_silence(
        self,
        audio: np.ndarray,
        sr: int,
        threshold_db: float = -40.0,
        min_silence_ms: float = 500.0,
    ) -> np.ndarray:
        """Remove silent segments longer than *min_silence_ms*."""
        frame_length = int(0.025 * sr)  # 25 ms frames
        hop_length = int(0.010 * sr)    # 10 ms hop

        # Frame-level RMS
        n_frames = 1 + (len(audio) - frame_length) // hop_length
        rms_db = np.full(n_frames, -np.inf)
        for i in range(n_frames):
            start = i * hop_length
            frame = audio[start : start + frame_length]
            rms = np.sqrt(np.mean(frame**2) + 1e-12)
            rms_db[i] = 20.0 * np.log10(rms + 1e-12)

        is_silent = rms_db < threshold_db
        min_silent_frames = int((min_silence_ms / 1000.0) * sr / hop_length)

        # Identify non-silent intervals (sample indices)
        keep: list[tuple[int, int]] = []
        silent_run = 0
        seg_start: int | None = None
        for i, s in enumerate(is_silent):
            if s:
                if seg_start is not None:
                    silent_run += 1
                else:
                    silent_run += 1
            else:
                if silent_run >= min_silent_frames and keep:
                    # long silence — skip it (already ended previous keep)
                    pass
                if seg_start is None:
                    seg_start = i * hop_length
                silent_run = 0

            if not s:
                seg_start = seg_start if seg_start is not None else i * hop_length

            # If we transition from non-silent to long silence, close segment
            if s and silent_run == min_silent_frames and seg_start is not None:
                end_sample = max((i - min_silent_frames + 1) * hop_length, seg_start)
                keep.append((seg_start, end_sample))
                seg_start = None

        # Close final segment
        if seg_start is not None:
            keep.append((seg_start, len(audio)))

        if not keep:
            return audio  # nothing to cut

        return np.concatenate([audio[s:e] for s, e in keep])

    # ------------------------------------------------------------------
    # Pitch shift
    # ------------------------------------------------------------------
    def pitch_shift(
        self,
        audio: np.ndarray,
        sr: int,
        semitones: float = 0.0,
    ) -> np.ndarray:
        """Pitch-shift using librosa. Semitones clamped to [-12, 12]."""
        import librosa

        semitones = float(np.clip(semitones, -12, 12))
        if semitones == 0.0:
            return audio.copy()
        return librosa.effects.pitch_shift(y=audio, sr=sr, n_steps=semitones)

    # ------------------------------------------------------------------
    # Time stretch
    # ------------------------------------------------------------------
    def time_stretch(
        self,
        audio: np.ndarray,
        sr: int,
        rate: float = 1.0,
    ) -> np.ndarray:
        """Time-stretch using librosa. Rate clamped to [0.5, 2.0]."""
        import librosa

        rate = float(np.clip(rate, 0.5, 2.0))
        if rate == 1.0:
            return audio.copy()
        return librosa.effects.time_stretch(y=audio, rate=rate)

    # ------------------------------------------------------------------
    # Loudness normalization (RMS-based LUFS approximation)
    # ------------------------------------------------------------------
    def normalize_loudness(
        self,
        audio: np.ndarray,
        sr: int,
        target_lufs: float = -14.0,
    ) -> np.ndarray:
        """Scale audio so RMS-based loudness ≈ *target_lufs* dBFS."""
        rms = np.sqrt(np.mean(audio**2) + 1e-12)
        current_db = 20.0 * np.log10(rms + 1e-12)
        gain = 10.0 ** ((target_lufs - current_db) / 20.0)
        return (audio * gain).astype(audio.dtype)

    # ------------------------------------------------------------------
    # EQ presets
    # ------------------------------------------------------------------
    def apply_eq(
        self,
        audio: np.ndarray,
        sr: int,
        preset: str = "flat",
    ) -> np.ndarray:
        """Apply EQ preset using cascaded biquad filters."""
        if preset == "flat":
            return audio.copy()

        nyq = sr / 2.0
        result = audio.astype(np.float64)

        if preset == "voice":
            # Cut below 100 Hz
            sos_hp = butter(4, 100.0 / nyq, btype="high", output="sos")
            result = sosfilt(sos_hp, result)
            # Boost 300-3000 Hz (bandpass, then mix)
            sos_bp = butter(2, [300.0 / nyq, 3000.0 / nyq], btype="band", output="sos")
            boosted = sosfilt(sos_bp, result)
            result = result + 0.4 * boosted

        elif preset == "music":
            # Slight bass boost (< 250 Hz)
            sos_lp = butter(2, 250.0 / nyq, btype="low", output="sos")
            bass = sosfilt(sos_lp, result)
            result = result + 0.25 * bass
            # Treble boost (> 6 kHz)
            if 6000.0 < nyq:
                sos_hp = butter(2, 6000.0 / nyq, btype="high", output="sos")
                treble = sosfilt(sos_hp, result)
                result = result + 0.2 * treble

        elif preset == "podcast":
            # Cut < 80 Hz
            sos_hp = butter(4, 80.0 / nyq, btype="high", output="sos")
            result = sosfilt(sos_hp, result)
            # Boost 2-4 kHz
            upper = min(4000.0, nyq - 1)
            if 2000.0 < upper:
                sos_bp = butter(2, [2000.0 / nyq, upper / nyq], btype="band", output="sos")
                presence = sosfilt(sos_bp, result)
                result = result + 0.35 * presence
            # Gentle compression (simple soft-knee)
            threshold = np.percentile(np.abs(result), 90)
            mask = np.abs(result) > threshold
            result[mask] = np.sign(result[mask]) * (
                threshold + (np.abs(result[mask]) - threshold) * 0.5
            )
        else:
            raise ValueError(f"Unknown EQ preset: {preset}")

        return result.astype(audio.dtype)

    # ------------------------------------------------------------------
    # Speech enhance (preset chain)
    # ------------------------------------------------------------------
    def speech_enhance(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Convenience chain: silence removal → denoise → loudness → voice EQ."""
        out = self.remove_silence(audio, sr)
        out = self.denoise(out, sr)
        out = self.normalize_loudness(out, sr, target_lufs=-14.0)
        out = self.apply_eq(out, sr, preset="voice")
        return out

    # ------------------------------------------------------------------
    # Generic chain runner
    # ------------------------------------------------------------------
    _OP_MAP = {
        "denoise": "denoise",
        "silence": "remove_silence",
        "pitch": "pitch_shift",
        "stretch": "time_stretch",
        "loudness": "normalize_loudness",
        "eq": "apply_eq",
        "enhance": "speech_enhance",
    }

    def apply_chain(
        self,
        audio: np.ndarray,
        sr: int,
        steps: list[dict],
    ) -> tuple[np.ndarray, list[str]]:
        """Apply a sequence of transform steps.

        Each step: ``{"op": "<name>", "params": {…}}``.
        Returns ``(result_audio, list_of_applied_op_names)``.
        """
        applied: list[str] = []
        result = audio.copy()
        for step in steps:
            op = step.get("op", "")
            params = step.get("params", {})
            method_name = self._OP_MAP.get(op)
            if method_name is None:
                raise ValueError(f"Unknown transform op: {op}")
            method = getattr(self, method_name)
            result = method(result, sr, **params)
            applied.append(op)
        return result, applied


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _match_length(arr: np.ndarray, target_len: int) -> np.ndarray:
    """Trim or zero-pad *arr* to *target_len*."""
    if len(arr) >= target_len:
        return arr[:target_len]
    return np.pad(arr, (0, target_len - len(arr)))
