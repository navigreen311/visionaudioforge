"""Tests for the audio augmentation pipeline."""

from __future__ import annotations

import io
import json

import numpy as np
import pytest
import soundfile as sf

from app.services.audio.augmentation import AudioAugmenter
from app.services.audio.augmentation_presets import PRESETS

SR = 22050


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_sine_wave(freq: float = 440.0, duration: float = 1.0, sr: int = SR) -> np.ndarray:
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _wav_bytes(audio: np.ndarray, sr: int = SR) -> bytes:
    """Encode audio to in-memory WAV bytes."""
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Unit tests — AudioAugmenter
# ---------------------------------------------------------------------------

augmenter = AudioAugmenter()


def test_add_white_noise_changes_signal():
    audio = create_sine_wave()
    noisy = augmenter.add_noise(audio, SR, noise_type="white", snr_db=20)
    assert not np.allclose(audio, noisy), "Noise should change the signal"


def test_add_noise_preserves_length():
    audio = create_sine_wave()
    for noise_type in ("white", "pink", "brown"):
        noisy = augmenter.add_noise(audio, SR, noise_type=noise_type, snr_db=15)
        assert len(noisy) == len(audio), f"{noise_type} noise changed length"


def test_time_stretch_faster():
    audio = create_sine_wave(duration=2.0)
    stretched = augmenter.time_stretch(audio, SR, rate=1.5)
    assert len(stretched) < len(audio), "Faster rate should produce shorter output"


def test_time_stretch_slower():
    audio = create_sine_wave(duration=2.0)
    stretched = augmenter.time_stretch(audio, SR, rate=0.7)
    assert len(stretched) > len(audio), "Slower rate should produce longer output"


def test_pitch_shift_preserves_duration():
    audio = create_sine_wave()
    shifted = augmenter.pitch_shift(audio, SR, n_steps=3)
    tolerance = SR * 0.1  # 100ms tolerance
    assert abs(len(shifted) - len(audio)) < tolerance, "Pitch shift should roughly preserve duration"


def test_time_shift_positive():
    audio = create_sine_wave()
    shifted = augmenter.time_shift(audio, SR, shift_ms=100)
    n_pad = int(SR * 100 / 1000)
    assert np.allclose(shifted[:n_pad], 0.0), "Positive shift should zero-pad the start"


def test_time_shift_negative():
    audio = create_sine_wave()
    shifted = augmenter.time_shift(audio, SR, shift_ms=-100)
    n_trim = int(SR * 100 / 1000)
    assert np.allclose(shifted[-n_trim:], 0.0), "Negative shift should zero-pad the end"


def test_frequency_mask_zeros_bands():
    spec = np.ones((128, 100))
    masked = augmenter.frequency_mask(spec, num_masks=1, mask_width=10)
    # At least one full row should be zeroed
    zero_rows = np.where(np.all(masked == 0, axis=1))[0]
    assert len(zero_rows) > 0, "frequency_mask should zero out at least one frequency band"


def test_time_mask_zeros_bands():
    spec = np.ones((128, 100))
    masked = augmenter.time_mask(spec, num_masks=1, mask_width=10)
    zero_cols = np.where(np.all(masked == 0, axis=0))[0]
    assert len(zero_cols) > 0, "time_mask should zero out at least one time band"


def test_pipeline_applies_with_probability():
    """Run pipeline 100 times with p=0.5; expect ~50% application rate."""
    audio = create_sine_wave()
    config = [{"type": "noise", "probability": 0.5, "params": {"snr_db": 10}}]
    changed_count = 0
    for _ in range(100):
        result, applied = augmenter.apply_pipeline(audio, SR, config)
        if len(applied) > 0:
            changed_count += 1
    # Allow wide margin: 20-80% would be extremely unlikely to fail
    assert 20 <= changed_count <= 80, f"Expected ~50% application, got {changed_count}%"


def test_augment_batch():
    audio_list = [create_sine_wave(), create_sine_wave(freq=880)]
    config = [{"type": "noise", "probability": 1.0, "params": {"snr_db": 15}}]
    results = augmenter.augment_batch(audio_list, SR, config, num_versions=3)
    assert len(results) == 2
    assert all(len(versions) == 3 for versions in results)


# ---------------------------------------------------------------------------
# Preset validation
# ---------------------------------------------------------------------------

def test_preset_configs_are_valid():
    valid_types = {"noise", "stretch", "pitch", "shift"}
    for name, steps in PRESETS.items():
        assert isinstance(steps, list), f"Preset {name} should be a list"
        for step in steps:
            assert step["type"] in valid_types, f"Invalid type in preset {name}: {step['type']}"
            assert 0.0 <= step.get("probability", 1.0) <= 1.0, f"Bad probability in {name}"
            assert isinstance(step.get("params", {}), dict), f"Bad params in {name}"


# ---------------------------------------------------------------------------
# API integration test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_augment_endpoint(client):
    audio = create_sine_wave(duration=0.5)
    wav_data = _wav_bytes(audio)

    response = await client.post(
        "/api/audio/augment",
        files={"file": ("test.wav", wav_data, "audio/wav")},
        data={"config": "light"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert "augmented_audio" in body
    assert "applied_augmentations" in body
    assert body["original_duration_s"] > 0


@pytest.mark.anyio
async def test_api_augment_custom_config(client):
    audio = create_sine_wave(duration=0.5)
    wav_data = _wav_bytes(audio)
    custom = json.dumps([{"type": "noise", "probability": 1.0, "params": {"snr_db": 20}}])

    response = await client.post(
        "/api/audio/augment",
        files={"file": ("test.wav", wav_data, "audio/wav")},
        data={"config": custom},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["applied_augmentations"]) == 1
    assert body["applied_augmentations"][0]["type"] == "noise"
