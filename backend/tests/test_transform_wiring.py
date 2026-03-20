"""Tests for advanced transform wiring — verify all endpoints exist and function."""

from __future__ import annotations

import json

import numpy as np
import pytest
from httpx import AsyncClient

from tests.utils import audio_to_wav_bytes, create_test_audio, create_test_image, image_to_png_bytes


# ===================================================================
# Audio endpoint existence tests
# ===================================================================

AUDIO_ENDPOINTS = [
    "/api/transform/audio/denoise",
    "/api/transform/audio/silence-remove",
    "/api/transform/audio/pitch-shift",
    "/api/transform/audio/time-stretch",
    "/api/transform/audio/eq",
    "/api/transform/audio/chain",
    "/api/transform/audio/voice-convert",
    "/api/transform/audio/chapters",
    "/api/transform/audio/noise-profile",
    "/api/transform/audio/tts",
    "/api/transform/audio/batch",
]


@pytest.mark.anyio
async def test_all_audio_endpoints_exist(client: AsyncClient, test_audio: bytes):
    """Every audio endpoint must respond with something other than 404/405."""
    for ep in AUDIO_ENDPOINTS:
        if ep == "/api/transform/audio/tts":
            # TTS uses JSON body, not form data
            resp = await client.post(ep, json={"text": "hello", "voice": "default"})
        elif ep == "/api/transform/audio/chain":
            resp = await client.post(
                ep,
                files={"file": ("test.wav", test_audio, "audio/wav")},
                data={"steps": json.dumps([{"op": "denoise", "params": {}}])},
            )
        elif ep == "/api/transform/audio/batch":
            resp = await client.post(
                ep,
                files=[("files", ("test.wav", test_audio, "audio/wav"))],
                data={"operations": json.dumps([{"op": "denoise"}])},
            )
        else:
            resp = await client.post(
                ep,
                files={"file": ("test.wav", test_audio, "audio/wav")},
            )
        assert resp.status_code not in (404, 405, 501), (
            f"Endpoint {ep} returned {resp.status_code} — not wired"
        )


# ===================================================================
# Video endpoint existence tests
# ===================================================================

VIDEO_ENDPOINTS = [
    "/api/transform/video/background-remove",
    "/api/transform/video/super-resolution",
    "/api/transform/video/style",
    "/api/transform/video/auto-crop",
    "/api/transform/video/inpaint",
    "/api/transform/video/color-grade",
    "/api/transform/video/subtitle",
    "/api/transform/video/interpolate",
    "/api/transform/video/smart-crop",
    "/api/transform/video/highlight",
    "/api/transform/video/batch",
]


@pytest.mark.anyio
async def test_all_video_endpoints_exist(client: AsyncClient, test_image: bytes):
    """Every video endpoint must respond with something other than 404/405."""
    for ep in VIDEO_ENDPOINTS:
        if ep == "/api/transform/video/interpolate":
            resp = await client.post(
                ep,
                files=[
                    ("frame1", ("f1.png", test_image, "image/png")),
                    ("frame2", ("f2.png", test_image, "image/png")),
                ],
                data={"count": "1"},
            )
        elif ep == "/api/transform/video/highlight":
            resp = await client.post(
                ep,
                files=[
                    ("files", ("f1.png", test_image, "image/png")),
                    ("files", ("f2.png", test_image, "image/png")),
                ],
                data={"scores": json.dumps([0.5, 0.9]), "top_k": "1"},
            )
        elif ep == "/api/transform/video/subtitle":
            resp = await client.post(
                ep,
                files={"file": ("test.png", test_image, "image/png")},
                data={"text": "Hello", "position": "bottom"},
            )
        elif ep == "/api/transform/video/inpaint":
            resp = await client.post(
                ep,
                files=[
                    ("file", ("test.png", test_image, "image/png")),
                    ("mask", ("mask.png", test_image, "image/png")),
                ],
            )
        elif ep == "/api/transform/video/thumbnail":
            resp = await client.post(
                ep,
                files=[("files", ("f1.png", test_image, "image/png"))],
            )
        elif ep == "/api/transform/video/batch":
            resp = await client.post(
                ep,
                files=[("files", ("test.png", test_image, "image/png"))],
                data={"operation": "color_grade", "params": json.dumps({"preset": "cinematic"})},
            )
        else:
            resp = await client.post(
                ep,
                files={"file": ("test.png", test_image, "image/png")},
            )
        assert resp.status_code not in (404, 405, 501), (
            f"Endpoint {ep} returned {resp.status_code} — not wired"
        )


# ===================================================================
# Presets endpoint
# ===================================================================


@pytest.mark.anyio
async def test_presets_list_returns_all(client: AsyncClient):
    """GET /api/transform/presets must return audio and video presets."""
    resp = await client.get("/api/transform/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data
    assert "video" in data
    # Audio presets
    assert "podcast_cleanup" in data["audio"]
    assert "voice_enhancement" in data["audio"]
    assert "music_master" in data["audio"]
    assert "interview_cleanup" in data["audio"]
    # Video presets
    assert "social_media" in data["video"]
    assert "cinematic" in data["video"]
    assert "thumbnail" in data["video"]
    # Each preset must have description and operations
    for category in ("audio", "video"):
        for name, preset in data[category].items():
            assert "description" in preset, f"Preset {name} missing description"
            assert "operations" in preset, f"Preset {name} missing operations"


# ===================================================================
# Batch processing tests
# ===================================================================


@pytest.mark.anyio
async def test_batch_audio_processes_multiple(client: AsyncClient, test_audio: bytes):
    """Batch audio endpoint should process multiple files."""
    resp = await client.post(
        "/api/transform/audio/batch",
        files=[
            ("files", ("a1.wav", test_audio, "audio/wav")),
            ("files", ("a2.wav", test_audio, "audio/wav")),
        ],
        data={"operations": json.dumps([{"op": "denoise"}])},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files"] == 2
    assert len(data["results"]) == 2
    for r in data["results"]:
        assert r["status"] == "ok"


# ===================================================================
# Specific endpoint tests
# ===================================================================


@pytest.mark.anyio
async def test_api_voice_convert(client: AsyncClient, test_audio: bytes):
    """Voice conversion endpoint should return converted audio."""
    resp = await client.post(
        "/api/transform/audio/voice-convert",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"target_voice": "robotic"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data
    assert data["target_voice"] == "robotic"
    assert data["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_api_chapters(client: AsyncClient):
    """Chapters endpoint should return chapter list."""
    # Create audio with a long silence in the middle to produce chapters
    sr = 22050
    tone = create_test_audio(duration=0.5, sr=sr)
    silence = np.zeros(int(3.0 * sr), dtype=np.float32)
    audio_with_gap = np.concatenate([tone, silence, tone])
    wav_bytes = audio_to_wav_bytes(audio_with_gap, sr=sr)

    resp = await client.post(
        "/api/transform/audio/chapters",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
        data={"min_silence": "2.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "chapters" in data
    assert "total_chapters" in data
    assert data["total_chapters"] >= 2


@pytest.mark.anyio
async def test_api_color_grade(client: AsyncClient, test_image: bytes):
    """Color grade endpoint should return graded image."""
    resp = await client.post(
        "/api/transform/video/color-grade",
        files={"file": ("test.png", test_image, "image/png")},
        data={"preset": "vintage"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "image" in data
    assert data["preset"] == "vintage"


@pytest.mark.anyio
async def test_api_subtitle(client: AsyncClient, test_image: bytes):
    """Subtitle endpoint should return image with burned subtitle."""
    resp = await client.post(
        "/api/transform/video/subtitle",
        files={"file": ("test.png", test_image, "image/png")},
        data={"text": "Hello World", "position": "top"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "image" in data
    assert data["text"] == "Hello World"
    assert data["position"] == "top"


@pytest.mark.anyio
async def test_api_tts(client: AsyncClient):
    """TTS endpoint should return placeholder audio."""
    resp = await client.post(
        "/api/transform/audio/tts",
        json={"text": "Hello world test", "voice": "default"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data
    assert data["voice"] == "default"
    assert data["text_length"] == len("Hello world test")


@pytest.mark.anyio
async def test_api_smart_crop(client: AsyncClient, test_image: bytes):
    """Smart crop endpoint should return cropped image."""
    resp = await client.post(
        "/api/transform/video/smart-crop",
        files={"file": ("test.png", test_image, "image/png")},
        data={"target_size": "50x50", "method": "center_of_mass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "image" in data
    assert data["target_size"] == [50, 50]
    assert data["method"] == "center_of_mass"


@pytest.mark.anyio
async def test_api_highlight(client: AsyncClient, test_image: bytes):
    """Highlight endpoint should return top-k frame indices."""
    resp = await client.post(
        "/api/transform/video/highlight",
        files=[
            ("files", ("f1.png", test_image, "image/png")),
            ("files", ("f2.png", test_image, "image/png")),
            ("files", ("f3.png", test_image, "image/png")),
        ],
        data={"scores": json.dumps([0.1, 0.9, 0.5]), "top_k": "2"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "top_indices" in data
    assert data["top_k"] == 2
    assert 1 in data["top_indices"]  # frame index 1 had score 0.9
