"""Tests for STT, VAD, source separation, and audio classification services."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.audio.vad import VoiceActivityDetector
from app.services.audio.separation import SourceSeparator
from app.services.audio.classification import AudioClassifier
from app.services.audio.stt import SpeechToTextService
from tests.utils import audio_to_wav_bytes, create_test_audio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 22050


def _sine_wave(freq: float = 440.0, duration: float = 1.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _silence(duration: float = 1.0, sr: int = SR) -> np.ndarray:
    return np.zeros(int(sr * duration), dtype=np.float32)


# ---------------------------------------------------------------------------
# VAD tests
# ---------------------------------------------------------------------------


class TestVAD:
    def test_vad_detects_speech_in_tone(self):
        """A loud sine wave should be classified as speech-like energy."""
        vad = VoiceActivityDetector()
        audio = _sine_wave(440.0, duration=0.5)
        frames = vad.detect(audio, SR)
        assert len(frames) > 0
        speech_frames = [f for f in frames if f["is_speech"]]
        assert len(speech_frames) > 0, "Sine wave should have speech-like energy"

    def test_vad_detects_silence(self):
        """Silence should produce no speech frames."""
        vad = VoiceActivityDetector()
        audio = _silence(0.5)
        frames = vad.detect(audio, SR)
        speech_frames = [f for f in frames if f["is_speech"]]
        assert len(speech_frames) == 0, "Silence should not be classified as speech"

    def test_speech_ratio_between_0_and_1(self):
        """Speech ratio must always be in [0, 1]."""
        vad = VoiceActivityDetector()

        ratio_tone = vad.get_speech_ratio(_sine_wave(), SR)
        assert 0.0 <= ratio_tone <= 1.0

        ratio_silence = vad.get_speech_ratio(_silence(), SR)
        assert 0.0 <= ratio_silence <= 1.0


# ---------------------------------------------------------------------------
# Source separation tests
# ---------------------------------------------------------------------------


class TestSourceSeparation:
    @pytest.mark.anyio
    async def test_frequency_separation_splits_audio(self):
        """Frequency-band fallback should return all requested stems."""
        sep = SourceSeparator()
        audio = _sine_wave(1000.0, duration=0.5)
        stems = await sep.separate(audio, SR)
        assert "vocals" in stems
        assert "bass" in stems
        assert "other" in stems
        for name, data in stems.items():
            assert isinstance(data, np.ndarray), f"Stem '{name}' should be ndarray"
            assert len(data) > 0, f"Stem '{name}' should not be empty"


# ---------------------------------------------------------------------------
# Audio classification tests
# ---------------------------------------------------------------------------


class TestAudioClassifier:
    def test_audio_classifier_detects_silence(self):
        """Near-zero amplitude should be classified as silence."""
        clf = AudioClassifier()
        audio = _silence(1.0)
        result = clf.classify_sound(audio, SR)
        assert result["category"] == "silence"
        assert 0.0 <= result["confidence"] <= 1.0
        assert "all_scores" in result

    def test_anomaly_detection_flags_outlier(self):
        """Audio with stats far from reference should be flagged anomalous."""
        clf = AudioClassifier()
        audio = _sine_wave(440.0) * 5.0  # very loud

        reference_stats = {
            "rms": {"mean": 0.01, "std": 0.002},
            "zcr": {"mean": 0.05, "std": 0.01},
            "spectral_centroid": {"mean": 500.0, "std": 50.0},
        }

        result = clf.detect_anomaly(audio, SR, reference_stats=reference_stats)
        assert result["is_anomaly"] is True
        assert result["anomaly_score"] > 3.0


# ---------------------------------------------------------------------------
# STT tests
# ---------------------------------------------------------------------------


class TestSTT:
    @pytest.mark.anyio
    async def test_transcribe_fallback_when_no_whisper(self):
        """When whisper is unavailable, transcribe returns a helpful fallback."""
        stt = SpeechToTextService()
        # Force unavailable regardless of actual install
        stt.available = False

        audio = _sine_wave(440.0, duration=0.5)
        result = await stt.transcribe(audio, SR)

        assert "Whisper not installed" in result["text"]
        assert result["segments"] == []
        assert result["language"] == "unknown"
        assert result["duration_s"] > 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_vad_endpoint(client):
    """POST /api/audio/vad should return speech segments."""
    audio = create_test_audio(duration=0.5, sr=SR)
    wav_bytes = audio_to_wav_bytes(audio, sr=SR)

    resp = await client.post(
        "/api/audio/vad",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "segments" in data
    assert "speech_ratio" in data
    assert 0.0 <= data["speech_ratio"] <= 1.0


@pytest.mark.anyio
async def test_api_classify_endpoint(client):
    """POST /api/audio/classify should return a classification."""
    audio = create_test_audio(duration=0.5, sr=SR)
    wav_bytes = audio_to_wav_bytes(audio, sr=SR)

    resp = await client.post(
        "/api/audio/classify",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data
    assert "confidence" in data
    assert "all_scores" in data
