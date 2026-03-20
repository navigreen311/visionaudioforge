"""Comprehensive audio pipeline E2E tests.

Tests the full audio processing stack by importing and exercising actual
service classes directly — spectral analysis, augmentation, VAD,
classification, diarization, separation, fingerprinting, voice biometrics,
audio transforms, and call intelligence.
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from app.services.audio.spectral import SpectralAnalyzer
from app.services.audio.augmentation import AudioAugmenter
from app.services.audio.vad import VoiceActivityDetector
from app.services.audio.classification import AudioClassifier
from app.services.audio.diarization import SpeakerDiarizer
from app.services.audio.separation import SourceSeparator
from app.services.audio.fingerprinting import AudioFingerprinter
from app.services.audio.voice_biometrics import VoiceBiometrics
from app.services.transform.audio_transform import AudioTransformService
from app.services.audio.call_intelligence import CallIntelligence


pytestmark = [pytest.mark.integration, pytest.mark.e2e]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SR = 22050  # standard sample rate used across tests


def _sine_wave(freq: float = 440.0, duration: float = 1.0, sr: int = SR) -> np.ndarray:
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _silence(duration: float = 0.5, sr: int = SR) -> np.ndarray:
    """Generate digital silence."""
    return np.zeros(int(sr * duration), dtype=np.float32)


def _audio_with_gaps(sr: int = SR) -> np.ndarray:
    """Create audio that alternates between tone and silence."""
    tone = _sine_wave(440.0, 0.3, sr)
    gap = _silence(0.3, sr)
    return np.concatenate([tone, gap, tone, gap, tone])


def _noisy_audio(sr: int = SR) -> np.ndarray:
    """Create a sine wave with added white noise."""
    clean = _sine_wave(440.0, 1.0, sr)
    noise = 0.1 * np.random.randn(len(clean)).astype(np.float32)
    return clean + noise


def _multi_speaker_audio(sr: int = SR) -> np.ndarray:
    """Simulate two speakers with different frequency tones (3 seconds)."""
    speaker_a = _sine_wave(300.0, 1.0, sr)
    speaker_b = _sine_wave(800.0, 1.0, sr)
    speaker_a2 = _sine_wave(300.0, 1.0, sr)
    return np.concatenate([speaker_a, speaker_b, speaker_a2])


# ---------------------------------------------------------------------------
# 1. Spectral full pipeline
# ---------------------------------------------------------------------------
class TestSpectralFullPipeline:
    """Verify the full spectral analysis chain: STFT -> MEL -> MFCC -> stats."""

    def setup_method(self) -> None:
        self.analyzer = SpectralAnalyzer()
        self.audio = _sine_wave(440.0, 1.0)

    def test_compute_stft_shape(self) -> None:
        result = self.analyzer.compute_stft(self.audio, SR)
        assert "spectrogram" in result
        assert "magnitude" in result
        assert "phase" in result
        spec = result["spectrogram"]
        assert spec.ndim == 2
        # n_fft=2048 -> freq bins = 1025, time frames depend on hop
        assert spec.shape[0] == 1025

    def test_compute_mel_128_bins(self) -> None:
        result = self.analyzer.compute_mel_spectrogram(self.audio, SR, n_mels=128)
        mel = result["mel_spectrogram"]
        assert mel.shape[0] == 128, f"Expected 128 mel bins, got {mel.shape[0]}"

    def test_compute_mfcc_13_coeffs(self) -> None:
        result = self.analyzer.compute_mfcc(self.audio, SR, n_mfcc=13)
        mfcc = result["mfcc"]
        assert mfcc.shape[0] == 13, f"Expected 13 MFCC coeffs, got {mfcc.shape[0]}"
        assert "delta" in result
        assert "delta2" in result

    def test_waveform_stats(self) -> None:
        stats = self.analyzer.compute_waveform_stats(self.audio, SR)
        assert "duration_s" in stats
        assert "rms" in stats
        assert abs(stats["duration_s"] - 1.0) < 0.01, "Duration should be ~1 second"
        assert stats["rms"] > 0, "RMS should be positive for a sine wave"
        assert not stats["is_silent"]

    def test_full_chain(self) -> None:
        """Run the complete spectral pipeline end to end."""
        stft_result = self.analyzer.compute_stft(self.audio, SR)
        assert stft_result["spectrogram"].shape[0] == 1025

        mel_result = self.analyzer.compute_mel_spectrogram(self.audio, SR)
        assert mel_result["mel_spectrogram"].shape[0] == 128

        mfcc_result = self.analyzer.compute_mfcc(self.audio, SR)
        assert mfcc_result["mfcc"].shape[0] == 13

        stats = self.analyzer.compute_waveform_stats(self.audio, SR)
        assert abs(stats["duration_s"] - 1.0) < 0.01
        assert stats["rms"] > 0


# ---------------------------------------------------------------------------
# 2. Augmentation pipeline
# ---------------------------------------------------------------------------
class TestAugmentationPipeline:
    """Verify noise injection, time stretch, pitch shift, and pipeline."""

    def setup_method(self) -> None:
        self.augmenter = AudioAugmenter()
        self.audio = _sine_wave(440.0, 1.0)

    def test_add_noise_changes_audio(self) -> None:
        noisy = self.augmenter.add_noise(self.audio, SR, snr_db=10.0)
        assert noisy.shape == self.audio.shape
        assert not np.allclose(noisy, self.audio), "Noisy audio should differ from original"

    def test_time_stretch_shorter(self) -> None:
        stretched = self.augmenter.time_stretch(self.audio, SR, rate=1.5)
        # rate > 1 = faster = shorter output
        assert len(stretched) < len(self.audio), (
            f"Stretched audio ({len(stretched)}) should be shorter than original ({len(self.audio)})"
        )

    def test_pitch_shift_same_length(self) -> None:
        shifted = self.augmenter.pitch_shift(self.audio, SR, n_steps=2)
        assert len(shifted) == len(self.audio), "Pitch shift should preserve length"

    def test_apply_pipeline_three_ops(self) -> None:
        config = [
            {"type": "noise", "probability": 1.0, "params": {"snr_db": 20.0}},
            {"type": "stretch", "probability": 1.0, "params": {"rate": 1.2}},
            {"type": "pitch", "probability": 1.0, "params": {"n_steps": 1}},
        ]
        result, applied = self.augmenter.apply_pipeline(self.audio, SR, config)
        assert len(applied) == 3, f"Expected 3 applied ops, got {len(applied)}"
        assert result is not None
        assert len(result) > 0


# ---------------------------------------------------------------------------
# 3. VAD pipeline
# ---------------------------------------------------------------------------
class TestVADPipeline:
    """Verify voice activity detection on audio with silence gaps."""

    def setup_method(self) -> None:
        self.vad = VoiceActivityDetector()
        self.audio = _audio_with_gaps()

    def test_detect_returns_segments(self) -> None:
        frames = self.vad.detect(self.audio, SR)
        assert len(frames) > 0, "VAD should return frames"
        # Verify each frame has expected keys
        for f in frames:
            assert "start_s" in f
            assert "end_s" in f
            assert "is_speech" in f

    def test_speech_segments_found(self) -> None:
        segments = self.vad.get_speech_segments(self.audio, SR)
        assert len(segments) > 0, "Should detect at least one speech segment"
        for seg in segments:
            assert "start_s" in seg
            assert "end_s" in seg
            assert "duration_s" in seg

    def test_speech_ratio_in_range(self) -> None:
        ratio = self.vad.get_speech_ratio(self.audio, SR)
        assert 0.0 <= ratio <= 1.0, f"Speech ratio {ratio} should be between 0 and 1"


# ---------------------------------------------------------------------------
# 4. Classification
# ---------------------------------------------------------------------------
class TestClassification:
    """Verify audio classification returns category and confidence."""

    def setup_method(self) -> None:
        self.classifier = AudioClassifier()

    def test_classify_tone(self) -> None:
        tone = _sine_wave(440.0, 1.0)
        result = self.classifier.classify_sound(tone, SR)
        assert "category" in result, "Result should contain 'category'"
        assert "confidence" in result, "Result should contain 'confidence'"
        assert isinstance(result["category"], str)
        assert 0.0 <= result["confidence"] <= 1.0
        assert "all_scores" in result

    def test_classify_silence(self) -> None:
        silence = _silence(1.0)
        result = self.classifier.classify_sound(silence, SR)
        assert result["category"] == "silence"


# ---------------------------------------------------------------------------
# 5. Diarization
# ---------------------------------------------------------------------------
class TestDiarization:
    """Verify speaker diarization returns segments with labels and timestamps."""

    def setup_method(self) -> None:
        self.diarizer = SpeakerDiarizer()

    def test_diarize_segments(self) -> None:
        audio = _multi_speaker_audio()
        result = self.diarizer.diarize(audio, SR, num_speakers=2)
        assert "segments" in result
        assert "num_speakers" in result
        segments = result["segments"]
        assert len(segments) > 0, "Diarization should produce segments"
        for seg in segments:
            assert "speaker" in seg, "Each segment needs a speaker label"
            assert "start_s" in seg, "Each segment needs a start timestamp"
            assert "end_s" in seg, "Each segment needs an end timestamp"
            assert seg["end_s"] > seg["start_s"]

    def test_diarize_speaker_stats(self) -> None:
        audio = _multi_speaker_audio()
        result = self.diarizer.diarize(audio, SR, num_speakers=2)
        assert "speaker_stats" in result
        stats = result["speaker_stats"]
        assert len(stats) > 0


# ---------------------------------------------------------------------------
# 6. Source separation
# ---------------------------------------------------------------------------
class TestSeparation:
    """Verify audio source separation returns a dict of stems."""

    def setup_method(self) -> None:
        self.separator = SourceSeparator()

    @pytest.mark.asyncio
    async def test_separate_returns_stems(self) -> None:
        audio = _sine_wave(440.0, 1.0)
        result = await self.separator.separate(audio, SR)
        assert isinstance(result, dict), "Separation should return a dict"
        assert len(result) > 0, "Should return at least one stem"
        for stem_name, stem_audio in result.items():
            assert isinstance(stem_name, str)
            assert isinstance(stem_audio, np.ndarray)
            assert len(stem_audio) > 0


# ---------------------------------------------------------------------------
# 7. Fingerprinting
# ---------------------------------------------------------------------------
class TestFingerprinting:
    """Verify fingerprint generation and matching."""

    def setup_method(self) -> None:
        self.fp = AudioFingerprinter()
        self.audio = _sine_wave(440.0, 1.0)

    def test_generate_fingerprint_hash(self) -> None:
        result = self.fp.generate_fingerprint(self.audio, SR)
        assert "fingerprint" in result
        fp_hash = result["fingerprint"]
        assert isinstance(fp_hash, str)
        assert len(fp_hash) > 0, "Fingerprint hash should be non-empty"

    def test_match_same_audio(self) -> None:
        fp1 = self.fp.generate_fingerprint(self.audio, SR)
        fp2 = self.fp.generate_fingerprint(self.audio, SR)
        match_result = self.fp.match_fingerprints(fp1, fp2)
        assert match_result["match"] is True, "Same audio should match itself"
        assert match_result["similarity"] > 0.5


# ---------------------------------------------------------------------------
# 8. Voice biometrics
# ---------------------------------------------------------------------------
class TestVoiceBiometrics:
    """Verify voiceprint extraction and comparison."""

    def setup_method(self) -> None:
        self.bio = VoiceBiometrics()

    def test_extract_voiceprint_shape(self) -> None:
        audio = _sine_wave(440.0, 1.0)
        vp = self.bio.extract_voiceprint(audio, SR)
        assert vp.shape == (128,), f"Voiceprint shape should be (128,), got {vp.shape}"

    def test_compare_same_audio_high_similarity(self) -> None:
        audio = _sine_wave(440.0, 1.0)
        vp1 = self.bio.extract_voiceprint(audio, SR)
        vp2 = self.bio.extract_voiceprint(audio, SR)
        result = self.bio.compare_voiceprints(vp1, vp2)
        assert result["similarity"] > 0.9, (
            f"Same audio voiceprints should have high similarity, got {result['similarity']}"
        )
        assert result["is_same_speaker"] is True


# ---------------------------------------------------------------------------
# 9. Audio transform chain
# ---------------------------------------------------------------------------
class TestAudioTransformChain:
    """Verify denoise -> normalize -> EQ chain on noisy audio."""

    def setup_method(self) -> None:
        self.transform = AudioTransformService()

    def test_denoise_reduces_noise(self) -> None:
        noisy = _noisy_audio()
        denoised = self.transform.denoise(noisy, SR)
        assert len(denoised) == len(noisy)
        # Denoised signal should differ from the noisy input
        assert not np.allclose(denoised, noisy)

    def test_normalize_loudness(self) -> None:
        audio = _sine_wave(440.0, 1.0) * 0.01  # quiet signal
        normalized = self.transform.normalize_loudness(audio, SR, target_lufs=-14.0)
        # Normalized should be louder than the quiet input
        rms_before = float(np.sqrt(np.mean(audio ** 2)))
        rms_after = float(np.sqrt(np.mean(normalized ** 2)))
        assert rms_after > rms_before, "Normalization should increase loudness of quiet audio"

    def test_apply_eq_voice(self) -> None:
        audio = _sine_wave(440.0, 1.0)
        eq_result = self.transform.apply_eq(audio, SR, preset="voice")
        assert len(eq_result) == len(audio)
        # Voice EQ should modify the signal
        assert not np.allclose(eq_result, audio)

    def test_full_chain(self) -> None:
        """Run denoise -> normalize_loudness -> apply_eq('voice') end to end."""
        noisy = _noisy_audio()

        denoised = self.transform.denoise(noisy, SR)
        normalized = self.transform.normalize_loudness(denoised, SR, target_lufs=-14.0)
        eq_applied = self.transform.apply_eq(normalized, SR, preset="voice")

        assert len(eq_applied) > 0
        # Final output should differ from original noisy input
        min_len = min(len(eq_applied), len(noisy))
        assert not np.allclose(eq_applied[:min_len], noisy[:min_len]), (
            "Processed audio should differ from the noisy input"
        )


# ---------------------------------------------------------------------------
# 10. Call intelligence
# ---------------------------------------------------------------------------
class TestCallIntelligence:
    """Verify meeting summarization from transcript segments."""

    def setup_method(self) -> None:
        self.ci = CallIntelligence()

    def test_summarize_meeting(self) -> None:
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "We decided to move forward with the new design.",
                "start_s": 0.0,
                "end_s": 3.0,
            },
            {
                "speaker": "Speaker_1",
                "text": "I agree. The key point is we need to finalize by Friday.",
                "start_s": 3.0,
                "end_s": 6.0,
            },
            {
                "speaker": "Speaker_0",
                "text": "Action item: we will prepare the report by next week.",
                "start_s": 6.0,
                "end_s": 9.0,
            },
        ]
        result = self.ci.summarize_meeting(segments)
        assert "summary" in result, "Result should contain 'summary'"
        assert "key_points" in result, "Result should contain 'key_points'"
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0, "Summary should not be empty"

    def test_summarize_extracts_decisions(self) -> None:
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "We decided to launch next month. We agreed on the budget.",
                "start_s": 0.0,
                "end_s": 5.0,
            },
        ]
        result = self.ci.summarize_meeting(segments)
        assert "decisions" in result
        assert len(result["decisions"]) > 0, "Should extract at least one decision"

    def test_extract_action_items(self) -> None:
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "We will complete the review by Friday.",
                "start_s": 0.0,
                "end_s": 3.0,
            },
            {
                "speaker": "Speaker_1",
                "text": "I need to update the documentation.",
                "start_s": 3.0,
                "end_s": 6.0,
            },
        ]
        actions = self.ci.extract_action_items(segments)
        assert len(actions) > 0, "Should extract action items"
        for item in actions:
            assert "action" in item
            assert "speaker" in item
