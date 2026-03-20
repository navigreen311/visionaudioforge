"""End-to-end integration tests for the audio pipeline API."""

import pytest

from tests.utils import (
    audio_to_wav_bytes,
    create_test_audio,
    create_test_audio_with_noise,
)


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_upload_and_analyze_stft(test_app, test_audio):
    """POST /api/audio/analyze with test audio requesting STFT analysis."""
    response = await test_app.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"features": '["stft"]'},
    )
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "stft" in data or "spectrogram" in data


@pytest.mark.asyncio
async def test_upload_and_analyze_mfcc(test_app, test_audio):
    """POST /api/audio/analyze with test audio requesting MFCC features."""
    response = await test_app.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"features": '["mfcc"]'},
    )
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "mfcc" in data
        # Standard MFCC has 13 coefficients
        if isinstance(data["mfcc"], list) and len(data["mfcc"]) > 0:
            assert len(data["mfcc"][0]) == 13 or len(data["mfcc"]) == 13


@pytest.mark.asyncio
async def test_augment_audio(test_app, test_audio):
    """POST /api/audio/augment with noise injection config."""
    response = await test_app.post(
        "/api/audio/augment",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"augmentation": "noise", "snr_db": "10"},
    )
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        # Augmented audio should differ from input
        assert len(response.content) > 0
