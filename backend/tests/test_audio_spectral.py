"""Tests for the audio spectral analysis feature."""

from __future__ import annotations

import base64
import io
import json

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.audio.io import load_audio, save_audio
from app.services.audio.spectral import SpectralAnalyzer
from app.services.audio.visualization import (
    plot_mfcc,
    plot_spectrogram,
    plot_waveform,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 22050


def create_test_audio(
    duration: float = 1.0,
    sr: int = SR,
    freq: float = 440.0,
) -> np.ndarray:
    """Generate a pure sine tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _audio_to_wav_bytes(audio: np.ndarray, sr: int = SR) -> bytes:
    """Encode audio array as WAV bytes."""
    return save_audio(audio, sr, format="wav")


# ---------------------------------------------------------------------------
# SpectralAnalyzer unit tests
# ---------------------------------------------------------------------------

analyzer = SpectralAnalyzer()


def test_stft_shape():
    audio = create_test_audio()
    result = analyzer.compute_stft(audio, SR, n_fft=2048)
    # freq bins = n_fft // 2 + 1 = 1025
    assert result["magnitude"].shape[0] == 1025
    assert result["freqs"].shape[0] == 1025
    assert result["phase"].shape == result["magnitude"].shape


def test_mel_spectrogram_shape():
    audio = create_test_audio()
    result = analyzer.compute_mel_spectrogram(audio, SR, n_mels=128)
    assert result["mel_spectrogram"].shape[0] == 128


def test_mfcc_13_coefficients():
    audio = create_test_audio()
    result = analyzer.compute_mfcc(audio, SR, n_mfcc=13)
    assert result["mfcc"].shape[0] == 13


def test_delta_mfcc_computed():
    audio = create_test_audio()
    result = analyzer.compute_mfcc(audio, SR)
    assert result["delta"].shape == result["mfcc"].shape
    assert result["delta2"].shape == result["mfcc"].shape


def test_waveform_stats_valid():
    audio = create_test_audio()
    stats = analyzer.compute_waveform_stats(audio, SR)
    assert stats["duration_s"] > 0
    assert stats["rms"] > 0
    assert stats["peak_amplitude"] > 0
    assert stats["is_silent"] is False
    assert stats["sample_rate"] == SR


# ---------------------------------------------------------------------------
# I/O tests
# ---------------------------------------------------------------------------


def test_load_audio_from_bytes():
    audio = create_test_audio(duration=0.5)
    wav_bytes = _audio_to_wav_bytes(audio)
    loaded, sr = load_audio(wav_bytes)
    assert sr == SR
    assert len(loaded) > 0
    np.testing.assert_allclose(loaded, audio, atol=1e-4)


# ---------------------------------------------------------------------------
# Visualization tests
# ---------------------------------------------------------------------------


def test_visualization_returns_base64():
    audio = create_test_audio()
    stft = analyzer.compute_stft(audio, SR)
    b64 = plot_spectrogram(stft["magnitude"], SR)
    # Must be valid base64 — try decoding
    raw = base64.b64decode(b64)
    assert len(raw) > 100  # PNG header is at least ~100 bytes


def test_mfcc_visualization():
    audio = create_test_audio()
    mfcc = analyzer.compute_mfcc(audio, SR)
    b64 = plot_mfcc(mfcc["mfcc"], SR)
    raw = base64.b64decode(b64)
    assert len(raw) > 100


def test_waveform_visualization():
    audio = create_test_audio()
    b64 = plot_waveform(audio, SR)
    raw = base64.b64decode(b64)
    assert len(raw) > 100


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_api_audio_analyze_stft(client):
    audio = create_test_audio()
    wav_bytes = _audio_to_wav_bytes(audio)
    resp = await client.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
        data={"operations": json.dumps(["stft"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "stft" in body["features"]
    assert body["features"]["stft"]["shape"][0] == 1025
    assert body["audio_info"]["sample_rate"] == SR


@pytest.mark.anyio
async def test_api_audio_analyze_all(client):
    audio = create_test_audio(duration=0.5)
    wav_bytes = _audio_to_wav_bytes(audio)
    resp = await client.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
        data={"operations": json.dumps(["all"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "stft" in body["features"]
    assert "mel" in body["features"]
    assert "mfcc" in body["features"]
    assert "waveform" in body["features"]
    assert body["processing_time_ms"] > 0
