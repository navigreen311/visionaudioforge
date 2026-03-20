"""Tests for AdvancedAudioTransform and advanced audio API endpoints."""

from __future__ import annotations

import base64
import io

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.transform.audio_advanced import AdvancedAudioTransform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

svc = AdvancedAudioTransform()


def _tone(freq: float = 440.0, duration: float = 1.0, sr: int = 22050) -> tuple[np.ndarray, int]:
    """Generate a sine tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return 0.5 * np.sin(2 * np.pi * freq * t), sr


def _tone_silence_tone(sr: int = 22050) -> tuple[np.ndarray, int]:
    """1 s tone, 3 s silence, 1 s tone — should produce 2 chapters."""
    t1 = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t1)
    silence = np.zeros(3 * sr, dtype=np.float32)
    return np.concatenate([tone, silence, tone]), sr


def _wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestVoiceConversion:
    @pytest.mark.anyio
    async def test_voice_conversion_changes_audio(self):
        audio, sr = _tone()
        result = await svc.voice_conversion_stub(audio, sr, target_voice="male_deep")
        assert len(result) > 0
        assert result.dtype == audio.dtype
        # Audio should be different from original
        assert not np.allclose(audio, result, atol=1e-3)

    @pytest.mark.anyio
    async def test_voice_conversion_robotic(self):
        audio, sr = _tone()
        result = await svc.voice_conversion_stub(audio, sr, target_voice="robotic")
        assert len(result) == len(audio)
        assert not np.allclose(audio, result, atol=1e-3)

    @pytest.mark.anyio
    async def test_voice_conversion_whisper(self):
        audio, sr = _tone()
        result = await svc.voice_conversion_stub(audio, sr, target_voice="whisper")
        assert len(result) == len(audio)
        # Whisper should reduce overall amplitude
        assert np.sqrt(np.mean(result ** 2)) < np.sqrt(np.mean(audio ** 2))

    @pytest.mark.anyio
    async def test_voice_conversion_female_high(self):
        audio, sr = _tone()
        result = await svc.voice_conversion_stub(audio, sr, target_voice="female_high")
        assert len(result) > 0
        assert not np.allclose(audio, result, atol=1e-3)


class TestAutoChapter:
    @pytest.mark.anyio
    async def test_auto_chapter_detects_silences(self):
        audio, sr = _tone_silence_tone()
        chapters = await svc.auto_chapter(audio, sr, min_silence_s=2.0)
        assert len(chapters) >= 2
        # Each chapter should have required fields
        for ch in chapters:
            assert "chapter" in ch
            assert "start_s" in ch
            assert "end_s" in ch
            assert "duration_s" in ch
            assert ch["duration_s"] > 0

    @pytest.mark.anyio
    async def test_auto_chapter_single_no_silence(self):
        audio, sr = _tone(duration=2.0)
        chapters = await svc.auto_chapter(audio, sr, min_silence_s=2.0)
        assert len(chapters) == 1


class TestNoiseProfile:
    @pytest.mark.anyio
    async def test_noise_profile_returns_stats(self):
        # Create noisy audio
        audio, sr = _tone()
        rng = np.random.default_rng(42)
        noisy = audio + 0.1 * rng.standard_normal(len(audio)).astype(np.float32)

        profile = await svc.noise_profile(noisy, sr, segment_s=0.5)

        assert "noise_floor_db" in profile
        assert "snr_estimate_db" in profile
        assert "dominant_noise_freqs" in profile
        assert "recommendation" in profile
        assert isinstance(profile["noise_floor_db"], float)
        assert isinstance(profile["snr_estimate_db"], float)
        assert isinstance(profile["dominant_noise_freqs"], list)
        assert isinstance(profile["recommendation"], str)

    @pytest.mark.anyio
    async def test_noise_profile_clean_audio(self):
        audio, sr = _tone()
        profile = await svc.noise_profile(audio, sr)
        # Clean tone should have decent SNR
        assert profile["snr_estimate_db"] is not None


class TestTtsStub:
    @pytest.mark.anyio
    async def test_tts_stub_returns_audio(self):
        audio, sr = await svc.tts_stub("Hello world")
        assert sr == 22050
        assert len(audio) > 0
        assert audio.dtype == np.float32


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_api_voice_convert(client: AsyncClient):
    audio, sr = _tone(duration=0.5)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/transform/audio/voice-convert",
        files={"file": ("test.wav", wav, "audio/wav")},
        data={"target_voice": "robotic"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "audio" in body
    assert body["target_voice"] == "robotic"
    assert body["processing_time_ms"] >= 0

    # Verify decoded audio
    decoded = base64.b64decode(body["audio"])
    out_audio, out_sr = sf.read(io.BytesIO(decoded))
    assert len(out_audio) > 0


@pytest.mark.anyio
async def test_api_chapters(client: AsyncClient):
    audio, sr = _tone_silence_tone()
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/transform/audio/chapters",
        files={"file": ("test.wav", wav, "audio/wav")},
        data={"min_silence": "2.0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "chapters" in body
    assert body["total_chapters"] >= 2


@pytest.mark.anyio
async def test_api_noise_profile(client: AsyncClient):
    audio, sr = _tone(duration=1.0)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/transform/audio/noise-profile",
        files={"file": ("test.wav", wav, "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "noise_floor_db" in body
    assert "snr_estimate_db" in body
    assert "dominant_noise_freqs" in body
    assert "recommendation" in body
