"""Test utilities for generating synthetic test data and assertion helpers."""

import io
import struct
import uuid
import wave

import numpy as np


def create_test_image(
    width: int = 100, height: int = 100, color: tuple = (128, 128, 128)
) -> np.ndarray:
    """Create a solid-color RGB test image as uint8 ndarray."""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = color
    return image


def create_test_image_with_shapes(width: int = 200, height: int = 200) -> np.ndarray:
    """Create an RGB test image with a rectangle and circle drawn for detection testing."""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = (30, 30, 30)  # dark background

    # Draw a white rectangle (top-left region)
    image[20:80, 20:100] = (255, 255, 255)

    # Draw a filled circle (bottom-right region) using coordinate math
    cy, cx, r = 140, 140, 30
    y_coords, x_coords = np.ogrid[:height, :width]
    mask = (x_coords - cx) ** 2 + (y_coords - cy) ** 2 <= r**2
    image[mask] = (0, 200, 0)

    return image


def create_test_audio(
    duration: float = 1.0, sr: int = 22050, frequency: float = 440.0
) -> np.ndarray:
    """Generate a sine wave audio signal as float32 ndarray."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    signal = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    return signal


def create_test_audio_with_noise(
    duration: float = 1.0, sr: int = 22050, snr_db: float = 10.0
) -> np.ndarray:
    """Generate a sine wave with additive white noise at the specified SNR."""
    signal = create_test_audio(duration=duration, sr=sr)
    noise = np.random.default_rng(42).standard_normal(len(signal)).astype(np.float32)
    signal_power = np.mean(signal**2)
    noise_power = np.mean(noise**2)
    scale = np.sqrt(signal_power / (noise_power * 10 ** (snr_db / 10)))
    noisy = signal + scale * noise
    return noisy


def audio_to_wav_bytes(audio: np.ndarray, sr: int = 22050) -> bytes:
    """Convert a float32 audio ndarray to WAV file bytes."""
    buf = io.BytesIO()
    # Normalize to int16 range
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def image_to_png_bytes(image: np.ndarray) -> bytes:
    """Encode an RGB uint8 ndarray as PNG bytes using pure Python (no cv2/PIL dependency)."""
    try:
        from PIL import Image

        buf = io.BytesIO()
        img = Image.fromarray(image)
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: try cv2
        import cv2

        _, encoded = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return encoded.tobytes()


def create_test_user_data() -> dict:
    """Generate unique test user registration data."""
    uid = uuid.uuid4().hex[:8]
    return {
        "email": f"testuser_{uid}@example.com",
        "password": "TestPassword123!",
        "workspace_name": f"test-workspace-{uid}",
    }


def assert_response_shape(response, expected_keys: list) -> None:
    """Assert that all expected keys are present in the response JSON body."""
    data = response.json()
    for key in expected_keys:
        assert key in data, f"Expected key '{key}' not found in response. Got keys: {list(data.keys())}"


def assert_paginated_response(response) -> None:
    """Assert that the response has standard pagination fields."""
    data = response.json()
    for key in ("items", "total", "page", "size"):
        assert key in data, (
            f"Expected pagination key '{key}' not found in response. "
            f"Got keys: {list(data.keys())}"
        )
