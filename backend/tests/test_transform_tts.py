"""Tests for TTS, voice cloning, auto-dubbing, dereverberation, and compression."""

from __future__ import annotations

import base64
import io

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.transform.compressor import DynamicCompressor
from app.services.transform.dereverb import Dereverberation
from app.services.transform.dubbing import AutoDubber
from app.services.transform.tts import TTSService
from app.services.transform.voice_clone import VoiceCloneService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 22050


def _sine(freq: float = 440.0, duration: float = 1.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return 0.5 * np.sin(2 * np.pi * freq * t)


def _audio_upload_bytes(audio: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# TTS tests
# ---------------------------------------------------------------------------


class TestTTSService:
    def test_tts_synthesize_returns_audio(self):
        svc = TTSService()
        audio, sr = svc.synthesize("Hello world")
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 0
        assert sr == 22050

    def test_tts_voices_list(self):
        svc = TTSService()
        voices = svc.available_voices()
        assert len(voices) >= 5
        ids = {v["id"] for v in voices}
        assert {"default", "male", "female", "narrator", "child"} <= ids
        for v in voices:
            assert "id" in v
            assert "name" in v
            assert "language" in v
            assert "gender" in v

    def test_tts_voice_presets_produce_different_frequencies(self):
        svc = TTSService()
        audio_default, _ = svc.synthesize("Test tone", voice="default")
        audio_male, _ = svc.synthesize("Test tone", voice="male")
        # Different voice presets should produce different audio
        assert not np.allclose(audio_default, audio_male)

    def test_tts_speed_changes_duration(self):
        svc = TTSService()
        audio_normal, _ = svc.synthesize("Hello world test", speed=1.0)
        audio_fast, _ = svc.synthesize("Hello world test", speed=2.0)
        # Faster speed should produce shorter audio
        assert len(audio_fast) < len(audio_normal)

    def test_tts_ssml_with_break(self):
        svc = TTSService()
        ssml = '<speak>Hello<break time="500ms"/>world</speak>'
        audio, sr = svc.synthesize_ssml(ssml)
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 0


# ---------------------------------------------------------------------------
# Voice clone tests
# ---------------------------------------------------------------------------


class TestVoiceCloneService:
    def test_voice_clone_requires_consent(self):
        svc = VoiceCloneService()
        result = svc.check_consent("user1", "owner1")
        assert result["consent_given"] is False
        assert "consent" in result["note"].lower()

    def test_voice_clone_returns_stub(self):
        svc = VoiceCloneService()
        ref = _sine()
        result = svc.clone_voice(ref, SR, "Hello")
        assert result["audio"] is None
        assert "API" in result["note"]


# ---------------------------------------------------------------------------
# Auto-dubbing tests
# ---------------------------------------------------------------------------


class TestAutoDubber:
    def test_auto_dub_pipeline(self):
        dubber = AutoDubber()
        audio = _sine(duration=1.0)
        result = dubber.dub_audio(audio, SR, source_lang="en", target_lang="es")
        assert "dubbed_audio" in result
        assert isinstance(result["dubbed_audio"], np.ndarray)
        assert len(result["dubbed_audio"]) > 0
        assert result["source_lang"] == "en"
        assert result["target_lang"] == "es"
        assert "original_transcript" in result
        assert "translated_text" in result

    def test_estimate_dubbing_duration(self):
        dubber = AutoDubber()
        dur = dubber.estimate_dubbing_duration("Hello world, this is a test.", "en")
        assert dur > 0
        assert isinstance(dur, float)


# ---------------------------------------------------------------------------
# Dereverberation tests
# ---------------------------------------------------------------------------


class TestDereverberation:
    def test_dereverb_reduces_energy(self):
        dereverb = Dereverberation()
        # Create reverberant signal: original + delayed copy
        original = _sine(440, duration=1.0)
        delay_samples = int(0.05 * SR)
        reverb = np.zeros(len(original) + delay_samples, dtype=np.float32)
        reverb[: len(original)] += original
        reverb[delay_samples:] += 0.5 * original  # echo

        result = dereverb.remove_reverb(reverb, SR, strength=0.8)
        # Result energy should be less or equal to original reverb energy
        assert np.sum(result**2) <= np.sum(reverb**2) + 1e-6

    def test_rt60_estimation(self):
        dereverb = Dereverberation()
        # Short impulsive signal — should estimate small room
        impulse = np.zeros(SR, dtype=np.float32)
        impulse[0] = 1.0
        # Add quick decay
        decay = np.exp(-np.arange(SR) / (0.05 * SR)).astype(np.float32) * 0.5
        signal = impulse * decay

        result = dereverb.estimate_rt60(signal, SR)
        assert "rt60_ms" in result
        assert "room_size_estimate" in result
        assert result["rt60_ms"] > 0
        assert result["room_size_estimate"] in {"small", "medium", "large"}


# ---------------------------------------------------------------------------
# Compressor tests
# ---------------------------------------------------------------------------


class TestDynamicCompressor:
    def test_compressor_reduces_peaks(self):
        comp = DynamicCompressor()
        # Loud signal
        audio = _sine(440, duration=0.5) * 0.9
        result = comp.compress(audio, SR, threshold_db=-10, ratio=8.0)
        # Peak of compressed should be <= peak of original
        assert np.max(np.abs(result)) <= np.max(np.abs(audio)) + 1e-6

    def test_limiter_clips_ceiling(self):
        comp = DynamicCompressor()
        audio = _sine(440, duration=0.5) * 0.9
        ceiling_db = -6.0
        ceiling_linear = 10 ** (ceiling_db / 20.0)
        result = comp.apply_limiter(audio, SR, ceiling_db=ceiling_db)
        assert np.max(np.abs(result)) <= ceiling_linear + 1e-6

    def test_compressor_presets_valid(self):
        comp = DynamicCompressor()
        presets = comp.presets()
        assert "gentle" in presets
        assert "moderate" in presets
        assert "aggressive" in presets
        assert "broadcast" in presets
        for name, cfg in presets.items():
            assert "threshold_db" in cfg
            assert "ratio" in cfg

    def test_compressor_with_preset(self):
        comp = DynamicCompressor()
        audio = _sine(440, duration=0.5) * 0.8
        presets = comp.presets()
        p = presets["broadcast"]
        result = comp.compress(
            audio, SR,
            threshold_db=p["threshold_db"],
            ratio=p["ratio"],
            makeup_gain_db=p.get("makeup_gain_db", 0),
        )
        assert isinstance(result, np.ndarray)
        assert len(result) == len(audio)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_tts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/transform/audio/tts",
            data={"text": "Hello world", "voice": "default", "speed": "1.0"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data
    # Should be valid base64
    decoded = base64.b64decode(data["audio"])
    assert len(decoded) > 0


@pytest.mark.anyio
async def test_api_voices():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/transform/audio/voices")
    assert resp.status_code == 200
    data = resp.json()
    assert "voices" in data
    assert len(data["voices"]) >= 5


@pytest.mark.anyio
async def test_api_compress():
    transport = ASGITransport(app=app)
    audio = _sine(440, duration=0.5)
    wav_bytes = _audio_upload_bytes(audio)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/transform/audio/compress",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            data={"threshold": "-15", "ratio": "4.0", "preset": ""},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data


@pytest.mark.anyio
async def test_api_compressor_presets():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/transform/audio/compressor-presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    assert "broadcast" in data["presets"]
