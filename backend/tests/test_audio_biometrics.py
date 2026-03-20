"""Tests for voice biometrics, audio fingerprinting, AV sync, embeddings, and translation."""

from __future__ import annotations

import io

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.audio.voice_biometrics import VoiceBiometrics
from app.services.audio.fingerprinting import AudioFingerprinter
from app.services.audio.av_sync import AVSyncDetector
from app.services.audio.audio_embeddings import AudioEmbeddingService
from app.services.audio.translation import AudioTranslator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_bio = VoiceBiometrics()
_fp = AudioFingerprinter()
_sync = AVSyncDetector()
_emb = AudioEmbeddingService()
_trans = AudioTranslator()


def _tone(freq: float = 440.0, duration: float = 1.0, sr: int = 22050) -> tuple[np.ndarray, int]:
    """Generate a sine tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return 0.5 * np.sin(2 * np.pi * freq * t), sr


def _noise(duration: float = 1.0, sr: int = 22050) -> tuple[np.ndarray, int]:
    """Generate white noise."""
    rng = np.random.default_rng(99)
    return rng.standard_normal(int(sr * duration)).astype(np.float32), sr


def _wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Voice biometrics tests
# ---------------------------------------------------------------------------


class TestVoiceBiometrics:
    def test_voiceprint_shape_128(self):
        audio, sr = _tone()
        vp = _bio.extract_voiceprint(audio, sr)
        assert vp.shape == (128,)

    def test_voiceprint_normalized(self):
        audio, sr = _tone()
        vp = _bio.extract_voiceprint(audio, sr)
        norm = np.linalg.norm(vp)
        assert abs(norm - 1.0) < 1e-6, f"Voiceprint L2 norm should be ~1.0, got {norm}"

    def test_compare_same_audio_high_similarity(self):
        audio, sr = _tone()
        vp = _bio.extract_voiceprint(audio, sr)
        result = _bio.compare_voiceprints(vp, vp)
        assert result["similarity"] > 0.99
        assert result["is_same_speaker"] is True

    def test_compare_different_low_similarity(self):
        audio1, sr1 = _tone(freq=200.0)
        audio2, sr2 = _noise()
        vp1 = _bio.extract_voiceprint(audio1, sr1)
        vp2 = _bio.extract_voiceprint(audio2, sr2)
        result = _bio.compare_voiceprints(vp1, vp2)
        # Different signals should have lower similarity
        assert result["similarity"] < 0.95

    def test_enroll_speaker(self):
        samples = [_tone(freq=440.0), _tone(freq=445.0)]
        result = _bio.enroll_speaker("alice", samples)
        assert result["samples_used"] == 2
        assert "speaker_id" in result
        assert len(result["voiceprint"]) == 128

    def test_identify_speaker(self):
        audio1, sr1 = _tone(freq=440.0)
        audio2, sr2 = _tone(freq=440.0)
        vp1 = _bio.extract_voiceprint(audio1, sr1)
        enrolled = {"alice": vp1}
        result = _bio.identify_speaker(audio2, sr2, enrolled)
        assert result["speaker"] == "alice"
        assert result["confidence"] > 0.7


# ---------------------------------------------------------------------------
# Fingerprinting tests
# ---------------------------------------------------------------------------


class TestFingerprinting:
    def test_fingerprint_generates_hash(self):
        audio, sr = _tone(duration=2.0)
        fp = _fp.generate_fingerprint(audio, sr)
        assert isinstance(fp["fingerprint"], str)
        assert len(fp["fingerprint"]) == 64  # SHA-256 hex
        assert fp["peaks"] > 0
        assert fp["duration_s"] > 0

    def test_fingerprint_match_same_audio(self):
        audio, sr = _tone(duration=2.0)
        fp1 = _fp.generate_fingerprint(audio, sr)
        fp2 = _fp.generate_fingerprint(audio, sr)
        result = _fp.match_fingerprints(fp1, fp2)
        assert result["match"] is True
        assert result["similarity"] > 0.9

    def test_fingerprint_db_search(self):
        audio, sr = _tone(duration=2.0)
        fp = _fp.generate_fingerprint(audio, sr)
        db = _fp.create_fingerprint_db()
        db["song1"] = fp
        result = _fp.search_fingerprint(fp, db)
        assert result["matched_id"] == "song1"
        assert result["confidence"] > 0.9


# ---------------------------------------------------------------------------
# AV Sync tests
# ---------------------------------------------------------------------------


class TestAVSync:
    def test_av_sync_returns_offset(self):
        audio, sr = _tone(duration=2.0)
        # Synthetic video frames — brightness proportional to audio energy
        n_frames = 60  # 2s at 30fps
        samples_per_frame = len(audio) // n_frames
        video_frames = [
            np.array([np.sqrt(np.mean(audio[i * samples_per_frame : (i + 1) * samples_per_frame] ** 2))])
            for i in range(n_frames)
        ]
        result = _sync.detect_sync_offset(video_frames, audio, sr, fps=30.0)
        assert "offset_ms" in result
        assert "is_synced" in result
        assert "confidence" in result
        assert isinstance(result["offset_ms"], float)

    def test_lip_sync_stub(self):
        result = _sync.check_lip_sync([], [])
        assert result["sync_score"] == 0.65
        assert result["verdict"] == "moderate"


# ---------------------------------------------------------------------------
# Audio embedding tests
# ---------------------------------------------------------------------------


class TestAudioEmbeddings:
    def test_audio_embedding_shape_512(self):
        audio, sr = _tone()
        emb = _emb.embed_audio(audio, sr)
        assert emb.shape == (512,)

    def test_audio_embedding_spectral_model(self):
        audio, sr = _tone()
        emb = _emb.embed_audio(audio, sr, model="spectral")
        assert emb.shape == (512,)

    def test_batch_embedding(self):
        samples = [_tone(freq=440.0), _tone(freq=880.0)]
        result = _emb.embed_audio_batch(samples)
        assert result.shape == (2, 512)

    def test_audio_similarity_same(self):
        audio, sr = _tone()
        sim = _emb.compute_audio_similarity(audio, audio, sr)
        assert sim > 0.99


# ---------------------------------------------------------------------------
# Translation tests
# ---------------------------------------------------------------------------


class TestTranslation:
    def test_translation_stub_returns_original(self):
        result = _trans.translate_text("Hello world", "en", "es")
        assert result["translated_text"] == "Hello world"
        assert "note" in result
        assert "API" in result["note"]

    @pytest.mark.anyio
    async def test_translate_audio(self):
        audio, sr = _tone(duration=0.5)
        result = await _trans.translate_audio(audio, sr, "en", "es")
        assert "transcript" in result
        assert "translation" in result
        assert result["source_lang"] == "en"
        assert result["target_lang"] == "es"


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
async def test_api_voiceprint(client: AsyncClient):
    audio, sr = _tone(duration=0.5)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/audio/voiceprint",
        files={"file": ("test.wav", wav, "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "voiceprint" in body
    assert body["dimensions"] == 128


@pytest.mark.anyio
async def test_api_voiceprint_compare(client: AsyncClient):
    audio1, sr1 = _tone(freq=440.0, duration=0.5)
    audio2, sr2 = _tone(freq=440.0, duration=0.5)
    wav1 = _wav_bytes(audio1, sr1)
    wav2 = _wav_bytes(audio2, sr2)

    resp = await client.post(
        "/api/audio/voiceprint/compare",
        files=[
            ("file1", ("test1.wav", wav1, "audio/wav")),
            ("file2", ("test2.wav", wav2, "audio/wav")),
        ],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "similarity" in body
    assert "is_same_speaker" in body


@pytest.mark.anyio
async def test_api_fingerprint(client: AsyncClient):
    audio, sr = _tone(duration=1.0)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/audio/fingerprint",
        files={"file": ("test.wav", wav, "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "fingerprint" in body
    assert isinstance(body["fingerprint"], str)
    assert body["peaks"] > 0


@pytest.mark.anyio
async def test_api_fingerprint_match(client: AsyncClient):
    audio, sr = _tone(duration=1.0)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/audio/fingerprint/match",
        files=[
            ("file1", ("test1.wav", wav, "audio/wav")),
            ("file2", ("test2.wav", wav, "audio/wav")),
        ],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "match" in body
    assert "similarity" in body


@pytest.mark.anyio
async def test_api_embed(client: AsyncClient):
    audio, sr = _tone(duration=0.5)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/audio/embed",
        files={"file": ("test.wav", wav, "audio/wav")},
        data={"model": "mfcc_stats"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dimensions"] == 512
    assert len(body["embedding"]) == 512


@pytest.mark.anyio
async def test_api_translate(client: AsyncClient):
    audio, sr = _tone(duration=0.5)
    wav = _wav_bytes(audio, sr)

    resp = await client.post(
        "/api/audio/translate",
        files={"file": ("test.wav", wav, "audio/wav")},
        data={"source_lang": "en", "target_lang": "es"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "transcript" in body
    assert "translation" in body
