"""Advanced Audio Transform Service — voice conversion, auto-chapters, TTS stub, noise profiling."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, stft, istft


class AdvancedAudioTransform:
    """Advanced audio transforms: voice conversion, chapter detection, TTS, noise analysis."""

    # ------------------------------------------------------------------
    # Voice Conversion Stub
    # ------------------------------------------------------------------
    async def voice_conversion_stub(
        self,
        audio: np.ndarray,
        sr: int,
        target_voice: str = "male_deep",
    ) -> np.ndarray:
        """Apply voice conversion using pitch shift + formant approximation.

        Presets
        -------
        male_deep    : pitch_shift(-4) + lowpass boost
        female_high  : pitch_shift(+4) + highpass boost
        robotic      : add ring modulation (multiply with 30 Hz sine wave)
        whisper      : reduce amplitude of voiced segments, add slight noise
        """
        import librosa

        result = audio.astype(np.float64).copy()
        nyq = sr / 2.0

        if target_voice == "male_deep":
            result = librosa.effects.pitch_shift(
                y=result.astype(np.float32), sr=sr, n_steps=-4
            ).astype(np.float64)
            # Lowpass boost: amplify frequencies below 300 Hz
            cutoff = min(300.0, nyq - 1)
            sos_lp = butter(2, cutoff / nyq, btype="low", output="sos")
            bass = sosfilt(sos_lp, result)
            result = result + 0.4 * bass

        elif target_voice == "female_high":
            result = librosa.effects.pitch_shift(
                y=result.astype(np.float32), sr=sr, n_steps=4
            ).astype(np.float64)
            # Highpass boost: amplify frequencies above 2000 Hz
            cutoff = min(2000.0, nyq - 1)
            sos_hp = butter(2, cutoff / nyq, btype="high", output="sos")
            treble = sosfilt(sos_hp, result)
            result = result + 0.4 * treble

        elif target_voice == "robotic":
            # Ring modulation: multiply with a 30 Hz sine wave
            t = np.arange(len(result)) / sr
            modulator = np.sin(2 * np.pi * 30.0 * t)
            result = result * modulator

        elif target_voice == "whisper":
            # Reduce amplitude of voiced segments (high-energy frames) and add noise
            frame_len = int(0.025 * sr)
            hop_len = int(0.010 * sr)
            n_frames = max(1, 1 + (len(result) - frame_len) // hop_len)

            for i in range(n_frames):
                start = i * hop_len
                end = min(start + frame_len, len(result))
                frame = result[start:end]
                rms = np.sqrt(np.mean(frame ** 2) + 1e-12)
                rms_db = 20.0 * np.log10(rms + 1e-12)
                # Voiced segments are louder — reduce them
                if rms_db > -30.0:
                    result[start:end] *= 0.3

            # Add slight noise for breathy quality
            rng = np.random.default_rng(42)
            noise = 0.02 * rng.standard_normal(len(result))
            result = result + noise

        else:
            raise ValueError(f"Unknown target_voice preset: {target_voice}")

        return result.astype(audio.dtype)

    # ------------------------------------------------------------------
    # Auto Chapter Detection
    # ------------------------------------------------------------------
    async def auto_chapter(
        self,
        audio: np.ndarray,
        sr: int,
        min_silence_s: float = 2.0,
    ) -> list[dict]:
        """Detect long silences and split audio into chapters.

        Returns a list of dicts with chapter number, start/end/duration in seconds.
        """
        frame_length = int(0.025 * sr)  # 25 ms frames
        hop_length = int(0.010 * sr)    # 10 ms hop
        n_frames = max(1, 1 + (len(audio) - frame_length) // hop_length)

        # Compute frame-level RMS in dB
        rms_db = np.full(n_frames, -np.inf)
        for i in range(n_frames):
            start = i * hop_length
            frame = audio[start: start + frame_length]
            rms = np.sqrt(np.mean(frame ** 2) + 1e-12)
            rms_db[i] = 20.0 * np.log10(rms + 1e-12)

        silence_threshold_db = -40.0
        is_silent = rms_db < silence_threshold_db
        min_silent_frames = int(min_silence_s * sr / hop_length)

        # Find split points (centers of long silent regions)
        split_samples: list[int] = []
        silent_run_start: int | None = None
        silent_run_count = 0

        for i, s in enumerate(is_silent):
            if s:
                if silent_run_start is None:
                    silent_run_start = i
                silent_run_count += 1
            else:
                if silent_run_count >= min_silent_frames and silent_run_start is not None:
                    # Split at the center of the silence
                    center_frame = silent_run_start + silent_run_count // 2
                    split_samples.append(center_frame * hop_length)
                silent_run_start = None
                silent_run_count = 0

        # Check trailing silence
        if silent_run_count >= min_silent_frames and silent_run_start is not None:
            center_frame = silent_run_start + silent_run_count // 2
            split_samples.append(center_frame * hop_length)

        # Build chapters from split points
        total_duration = len(audio) / sr
        boundaries = [0] + split_samples + [len(audio)]
        chapters: list[dict] = []

        for idx in range(len(boundaries) - 1):
            start_s = boundaries[idx] / sr
            end_s = boundaries[idx + 1] / sr
            duration_s = end_s - start_s
            if duration_s > 0.01:  # skip near-zero segments
                chapters.append({
                    "chapter": len(chapters) + 1,
                    "start_s": round(start_s, 4),
                    "end_s": round(end_s, 4),
                    "duration_s": round(duration_s, 4),
                })

        return chapters

    # ------------------------------------------------------------------
    # TTS Stub
    # ------------------------------------------------------------------
    async def tts_stub(
        self,
        text: str,
        voice: str = "default",
    ) -> tuple[np.ndarray, int]:
        """Return a placeholder tone. Real TTS requires an external API
        (ElevenLabs, Google TTS, Azure Speech, etc.).

        Returns (audio_array, sample_rate).
        """
        sr = 22050
        duration = max(0.5, min(len(text) * 0.05, 5.0))  # scale with text length
        t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
        # Simple 440 Hz tone as placeholder
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)
        # NOTE: This is a placeholder. Integrate ElevenLabs, Google TTS, or
        # Azure Speech Services for production-quality text-to-speech.
        return tone, sr

    # ------------------------------------------------------------------
    # Noise Profile Analysis
    # ------------------------------------------------------------------
    async def noise_profile(
        self,
        audio: np.ndarray,
        sr: int,
        segment_s: float = 0.5,
    ) -> dict:
        """Analyze the first segment_s seconds as a noise profile.

        Returns noise floor, SNR estimate, dominant noise frequencies,
        and a recommendation string.
        """
        n_samples = min(int(segment_s * sr), len(audio))
        noise_segment = audio[:n_samples].astype(np.float64)

        # Compute spectral analysis of noise segment
        nperseg = min(1024, n_samples)
        if nperseg < 4:
            nperseg = n_samples

        f, t_bins, Zxx = stft(noise_segment, fs=sr, nperseg=nperseg)
        magnitude = np.abs(Zxx)

        # Noise floor: RMS of the noise segment in dB
        noise_rms = np.sqrt(np.mean(noise_segment ** 2) + 1e-12)
        noise_floor_db = round(float(20.0 * np.log10(noise_rms + 1e-12)), 2)

        # SNR estimate: compare full signal RMS to noise RMS
        signal_rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2) + 1e-12)
        snr_db = round(float(20.0 * np.log10(signal_rms / (noise_rms + 1e-12) + 1e-12)), 2)

        # Spectral mean and std
        spectral_mean = np.mean(magnitude, axis=1)

        # Dominant noise frequencies: top 5 frequency bins by mean magnitude
        top_k = min(5, len(f))
        top_indices = np.argsort(spectral_mean)[-top_k:][::-1]
        dominant_freqs = [round(float(f[i]), 1) for i in top_indices]

        # Recommendation
        if snr_db > 30:
            recommendation = "Audio is clean. Minimal processing needed."
        elif snr_db > 15:
            recommendation = "Moderate noise. Consider spectral gating denoise."
        elif snr_db > 5:
            recommendation = "Significant noise. Apply aggressive denoise and noise gate."
        else:
            recommendation = "Very noisy. Consider re-recording or heavy noise reduction."

        return {
            "noise_floor_db": noise_floor_db,
            "snr_estimate_db": snr_db,
            "dominant_noise_freqs": dominant_freqs,
            "recommendation": recommendation,
        }
