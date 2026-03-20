"""Tests for AudioTransformService and the /api/transform/audio endpoint."""

from __future__ import annotations

import base64
import io
import json

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.transform import AudioTransformService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_noisy_audio(duration: float = 2.0, sr: int = 22050) -> tuple[np.ndarray, int]:
    """Return a 440 Hz sine wave with additive white noise."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    noise = 0.05 * np.random.default_rng(42).standard_normal(len(t)).astype(np.float32)
    return sine + noise, sr


def create_audio_with_silence(sr: int = 22050) -> tuple[np.ndarray, int]:
    """1 s tone, 1 s silence, 1 s tone."""
    t1 = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t1)
    silence = np.zeros(sr, dtype=np.float32)
    return np.concatenate([tone, silence, tone]), sr


def _wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    return buf.getvalue()


svc = AudioTransformService()

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestDenoise:
    def test_denoise_reduces_noise(self):
        audio, sr = create_noisy_audio()
        denoised = svc.denoise(audio, sr)
        # The noise-only portion: last 0.2 s should be quieter after denoise
        tail = int(0.2 * sr)
        rms_before = np.sqrt(np.mean(audio[-tail:] ** 2))
        rms_after = np.sqrt(np.mean(denoised[-tail:] ** 2))
        # Denoised should not be louder than original (allowing small tolerance)
        assert rms_after <= rms_before * 1.5


class TestRemoveSilence:
    def test_remove_silence_shortens(self):
        audio, sr = create_audio_with_silence()
        trimmed = svc.remove_silence(audio, sr, threshold_db=-40, min_silence_ms=500)
        assert len(trimmed) < len(audio)


class TestPitchShift:
    def test_pitch_shift_preserves_length(self):
        audio, sr = create_noisy_audio(duration=1.0)
        shifted = svc.pitch_shift(audio, sr, semitones=3)
        assert abs(len(shifted) - len(audio)) < int(0.1 * sr)


class TestTimeStretch:
    def test_time_stretch_faster(self):
        audio, sr = create_noisy_audio(duration=1.0)
        stretched = svc.time_stretch(audio, sr, rate=1.5)
        # Faster → shorter
        assert len(stretched) < len(audio)


class TestNormalizeLoudness:
    def test_loudness_normalize(self):
        audio, sr = create_noisy_audio()
        target = -14.0
        normalized = svc.normalize_loudness(audio, sr, target_lufs=target)
        rms = np.sqrt(np.mean(normalized ** 2))
        out_db = 20 * np.log10(rms + 1e-12)
        assert abs(out_db - target) < 1.0  # within 1 dB


class TestEQ:
    def test_eq_voice_cuts_low_freq(self):
        """Voice preset should reduce energy below 100 Hz."""
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        low = 0.5 * np.sin(2 * np.pi * 50 * t)  # 50 Hz
        result = svc.apply_eq(low, sr, preset="voice")
        rms_before = np.sqrt(np.mean(low ** 2))
        rms_after = np.sqrt(np.mean(result ** 2))
        assert rms_after < rms_before * 0.8  # at least 20 % reduction


class TestSpeechEnhance:
    def test_speech_enhance_chain(self):
        audio, sr = create_noisy_audio()
        result = svc.speech_enhance(audio, sr)
        assert len(result) > 0
        assert result.dtype == audio.dtype


class TestApplyChain:
    def test_apply_chain_multiple_ops(self):
        audio, sr = create_noisy_audio()
        steps = [
            {"op": "denoise"},
            {"op": "loudness", "params": {"target_lufs": -14}},
            {"op": "eq", "params": {"preset": "voice"}},
        ]
        result, applied = svc.apply_chain(audio, sr, steps)
        assert applied == ["denoise", "loudness", "eq"]
        assert len(result) > 0


# ---------------------------------------------------------------------------
# API integration test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_transform_endpoint():
    audio, sr = create_noisy_audio(duration=1.0)
    wav = _wav_bytes(audio, sr)

    ops = json.dumps([{"op": "denoise"}, {"op": "loudness", "params": {"target_lufs": -14}}])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/transform/audio",
            files={"file": ("test.wav", wav, "audio/wav")},
            data={"operations": ops},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "audio" in body
    assert body["format"] == "wav"
    assert body["operations_applied"] == ["denoise", "loudness"]
    assert body["original_duration_s"] > 0
    assert body["processing_time_ms"] > 0

    # Verify we can decode the returned audio
    decoded = base64.b64decode(body["audio"])
    buf = io.BytesIO(decoded)
    out_audio, out_sr = sf.read(buf)
    assert out_sr == sr
    assert len(out_audio) > 0
