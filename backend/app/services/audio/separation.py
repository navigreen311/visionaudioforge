"""Audio source separation — Demucs when available, frequency-band fallback."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt


class SourceSeparator:
    """Separate audio into stems (vocals, drums, bass, other)."""

    def __init__(self) -> None:
        self.available = False
        try:
            import demucs  # noqa: F401

            self.available = True
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Frequency-band helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bandpass(audio: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
        sos = butter(5, [low, high], btype="band", fs=sr, output="sos")
        return sosfilt(sos, audio).astype(np.float32)

    @staticmethod
    def _lowpass(audio: np.ndarray, sr: int, cutoff: float) -> np.ndarray:
        sos = butter(5, cutoff, btype="low", fs=sr, output="sos")
        return sosfilt(sos, audio).astype(np.float32)

    @staticmethod
    def _highpass(audio: np.ndarray, sr: int, cutoff: float) -> np.ndarray:
        sos = butter(5, cutoff, btype="high", fs=sr, output="sos")
        return sosfilt(sos, audio).astype(np.float32)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def separate(
        self,
        audio: np.ndarray,
        sr: int,
        stems: list[str] | None = None,
    ) -> dict[str, np.ndarray]:
        """Separate *audio* into the requested stems.

        Falls back to simple frequency-band splitting when Demucs is not installed.
        """
        if stems is None:
            stems = ["vocals", "drums", "bass", "other"]

        if self.available:
            return await self._separate_demucs(audio, sr, stems)

        return self._separate_frequency(audio, sr, stems)

    async def _separate_demucs(
        self,
        audio: np.ndarray,
        sr: int,
        stems: list[str],
    ) -> dict[str, np.ndarray]:
        """Separate using Demucs."""
        import torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        model = get_model("htdemucs")
        model.eval()

        # Demucs expects (batch, channels, samples) at model.samplerate
        if sr != model.samplerate:
            import librosa

            audio = librosa.resample(audio, orig_sr=sr, target_sr=model.samplerate)

        tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        # tensor shape: (1, 1, samples)

        with torch.no_grad():
            sources = apply_model(model, tensor, device="cpu")

        # sources shape: (1, n_sources, channels, samples)
        source_names = model.sources
        result: dict[str, np.ndarray] = {}
        for i, name in enumerate(source_names):
            if name in stems:
                result[name] = sources[0, i].mean(dim=0).numpy().astype(np.float32)

        return result

    def _separate_frequency(
        self,
        audio: np.ndarray,
        sr: int,
        stems: list[str],
    ) -> dict[str, np.ndarray]:
        """Fallback: rough frequency-band separation."""
        nyquist = sr / 2.0
        result: dict[str, np.ndarray] = {}

        for stem in stems:
            if stem == "vocals":
                low = min(300.0, nyquist - 1)
                high = min(3000.0, nyquist - 1)
                if low < high:
                    result[stem] = self._bandpass(audio, sr, low, high)
                else:
                    result[stem] = audio.copy()
            elif stem == "bass":
                cutoff = min(300.0, nyquist - 1)
                result[stem] = self._lowpass(audio, sr, cutoff)
            elif stem == "drums":
                # drums: low-mid energy band 60-500 Hz
                low = min(60.0, nyquist - 1)
                high = min(500.0, nyquist - 1)
                if low < high:
                    result[stem] = self._bandpass(audio, sr, low, high)
                else:
                    result[stem] = audio.copy()
            else:  # "other"
                cutoff = min(3000.0, nyquist - 1)
                result[stem] = self._highpass(audio, sr, cutoff)

        return result

    async def extract_vocals(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Return only the vocal stem."""
        stems = await self.separate(audio, sr, stems=["vocals"])
        return stems["vocals"]

    async def remove_vocals(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Return the instrumental (audio minus vocal stem)."""
        vocals = await self.extract_vocals(audio, sr)
        # Match lengths in case filtering changed size
        min_len = min(len(audio), len(vocals))
        return (audio[:min_len] - vocals[:min_len]).astype(np.float32)
