"""Tests for M19 Safety+Privacy: plate blur, voice anonymization,
policy engine, provenance tracking, and compliance packs."""

from __future__ import annotations

import io
import struct
import wave
from uuid import uuid4

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)

from app.services.safety.plate_blur import PlateBlurService
from app.services.safety.voice_anon import VoiceAnonymizer
from app.services.safety.policy_engine import PolicyEngine, BUILT_IN_POLICIES
from app.services.safety.provenance import ProvenanceTracker
from app.services.safety.compliance import ComplianceManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_with_plate(w: int = 400, h: int = 300) -> np.ndarray:
    """Create a test image with a textured rectangle that has plate-like aspect ratio."""
    rng = np.random.default_rng(42)
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :] = (40, 40, 40)  # dark background
    # Draw a plate-like rectangle with varied pixel values (not solid)
    plate_w, plate_h = 140, 40
    x, y = 100, 150
    img[y : y + plate_h, x : x + plate_w] = rng.integers(100, 256, (plate_h, plate_w, 3), dtype=np.uint8)
    return img


def _make_wav_bytes(duration: float = 0.5, sr: int = 16000, freq: float = 440.0) -> bytes:
    """Generate a sine-wave WAV file as bytes."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Plate blur tests
# ---------------------------------------------------------------------------

class TestPlateBlur:
    def test_plate_blur_modifies_image(self):
        img = _make_image_with_plate()
        svc = PlateBlurService()
        # Manually provide a plate region so we guarantee a blur happens
        regions = [{"bbox": [100, 150, 140, 40], "confidence": 0.9}]
        blurred = svc.blur_plates(img, plate_regions=regions)
        # The blurred region should differ from the original
        roi_orig = img[150:190, 100:240]
        roi_blur = blurred[150:190, 100:240]
        assert not np.array_equal(roi_orig, roi_blur), "Blur should modify the plate region"

    def test_plate_redact_fills_black(self):
        img = _make_image_with_plate()
        svc = PlateBlurService()
        regions = [{"bbox": [100, 150, 140, 40], "confidence": 0.9}]
        redacted = svc.redact_plates(img, plate_regions=regions)
        roi = redacted[150:190, 100:240]
        assert np.all(roi == 0), "Redacted region should be all black"

    def test_detect_plates_returns_list(self):
        img = _make_image_with_plate()
        svc = PlateBlurService()
        plates = svc.detect_plates(img)
        assert isinstance(plates, list)


# ---------------------------------------------------------------------------
# Voice anonymization tests
# ---------------------------------------------------------------------------

class TestVoiceAnonymize:
    def test_voice_anonymize_pitch_changes(self):
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float64)
        anon = VoiceAnonymizer()
        result = anon.anonymize(audio, sr, method="pitch")
        assert result.shape == audio.shape
        # Pitch shift changes the frequency content — compare spectral energy
        fft_orig = np.abs(np.fft.rfft(audio))
        fft_result = np.abs(np.fft.rfft(result))
        peak_orig = np.argmax(fft_orig)
        peak_result = np.argmax(fft_result)
        assert peak_orig != peak_result, "Pitch shift should change the dominant frequency"

    def test_voice_anonymize_formant(self):
        sr = 16000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float64)
        anon = VoiceAnonymizer()
        result = anon.anonymize(audio, sr, method="formant")
        assert result.shape == audio.shape

    def test_voice_anonymize_noise_mask(self):
        sr = 16000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float64)
        anon = VoiceAnonymizer()
        result = anon.anonymize(audio, sr, method="noise_mask")
        assert result.shape == audio.shape
        assert not np.allclose(audio, result, atol=0.01)

    def test_anonymize_segments(self):
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float64)
        anon = VoiceAnonymizer()
        segments = [{"start": 0.2, "end": 0.5}]
        result = anon.anonymize_segments(audio, sr, segments, method="pitch")
        assert result.shape == audio.shape
        # Region outside segment should be unchanged
        assert np.array_equal(result[:1000], audio[:1000])


# ---------------------------------------------------------------------------
# Policy engine tests
# ---------------------------------------------------------------------------

class TestPolicyEngine:
    def test_policy_evaluation_blocks_pii(self):
        scan = {"pii_found": [{"type": "email", "value": "a@b.com"}], "faces_detected": 0, "risk_score": 0.1}
        policy = BUILT_IN_POLICIES["strict_pii"]
        result = PolicyEngine.evaluate_policy(policy, scan)
        assert result["allowed"] is False
        assert len(result["violations"]) > 0

    def test_policy_allows_clean(self):
        scan = {"pii_found": [], "faces_detected": 0, "risk_score": 0.0}
        policy = BUILT_IN_POLICIES["strict_pii"]
        result = PolicyEngine.evaluate_policy(policy, scan)
        assert result["allowed"] is True
        assert len(result["violations"]) == 0

    def test_export_check(self):
        scan_clean = {"pii_found": [], "faces_detected": 0, "risk_score": 0.0}
        result = PolicyEngine.check_export_allowed(scan_clean, "strict_pii")
        assert result["allowed"] is True

        scan_dirty = {"pii_found": [{"type": "ssn"}], "faces_detected": 0, "risk_score": 0.3}
        result2 = PolicyEngine.check_export_allowed(scan_dirty, "strict_pii")
        assert result2["allowed"] is False

    def test_voice_clone_consent(self):
        result = PolicyEngine.check_voice_clone_consent("user1", "owner1")
        assert result["consent"] is False

        PolicyEngine.record_voice_consent("user1", "owner1")
        result2 = PolicyEngine.check_voice_clone_consent("user1", "owner1")
        assert result2["consent"] is True

    def test_create_policy(self):
        rules = [{"type": "restrict_export", "condition": "pii_detected", "action": "block"}]
        policy = PolicyEngine.create_policy("test_policy", rules)
        assert policy["name"] == "test_policy"
        assert len(policy["rules"]) == 1

    def test_content_review_queues_high_risk(self):
        scan = {"pii_found": [], "faces_detected": 0, "risk_score": 0.8}
        policy = BUILT_IN_POLICIES["content_review"]
        result = PolicyEngine.evaluate_policy(policy, scan)
        assert result["allowed"] is True  # require_approval doesn't block
        assert len(result["required_actions"]) > 0


# ---------------------------------------------------------------------------
# Provenance tests
# ---------------------------------------------------------------------------

class TestProvenance:
    @pytest.mark.anyio
    async def test_provenance_chain(self):
        await requires_postgres()
        engine = await fresh_engine()
        factory = db_session_factory(engine)
        asset_id = f"asset-{uuid4().hex[:8]}"

        try:
            async with factory() as session:
                workspace_id = str(await seed_workspace(session, "provenance-chain"))
                tracker = ProvenanceTracker()
                await tracker.record_provenance(
                    session, asset_id, "created", "user-1", workspace_id=workspace_id
                )
                await tracker.record_provenance(
                    session,
                    asset_id,
                    "transformed",
                    "user-1",
                    {"op": "resize"},
                    workspace_id=workspace_id,
                )
                chain = await tracker.get_provenance_chain(session, asset_id)

            assert len(chain) == 2
            assert chain[0]["action"] == "created"
            assert chain[1]["action"] == "transformed"
            assert chain[1]["details"] == {"op": "resize"}
        finally:
            await engine.dispose()

    @pytest.mark.anyio
    async def test_rejects_an_unknown_action(self):
        await requires_postgres()
        engine = await fresh_engine()
        factory = db_session_factory(engine)
        try:
            async with factory() as session:
                with pytest.raises(ValueError, match="Invalid action"):
                    await ProvenanceTracker.record_provenance(
                        session, "asset-x", "teleported", "user-1"
                    )
        finally:
            await engine.dispose()

    @pytest.mark.anyio
    async def test_chain_is_scoped_to_its_workspace(self):
        """One workspace must not see another's provenance."""
        await requires_postgres()
        engine = await fresh_engine()
        factory = db_session_factory(engine)
        asset_id = f"shared-{uuid4().hex[:8]}"

        try:
            async with factory() as session:
                ours = str(await seed_workspace(session, "prov-ours"))
                theirs = str(await seed_workspace(session, "prov-theirs"))
                await ProvenanceTracker.record_provenance(
                    session, asset_id, "created", "u1", workspace_id=ours
                )
                await ProvenanceTracker.record_provenance(
                    session, asset_id, "exported", "u2", workspace_id=theirs
                )

                mine = await ProvenanceTracker.get_provenance_chain(
                    session, asset_id, workspace_id=ours
                )

            assert [e["action"] for e in mine] == ["created"]
        finally:
            await engine.dispose()

    @pytest.mark.anyio
    async def test_provenance_survives_a_restart(self):
        """Write through one engine, read through a brand-new one.

        A chain that vanishes on restart is worse than no chain: it reads as
        "nothing ever touched this asset" rather than as missing data.
        """
        await requires_postgres()
        engine = await fresh_engine()
        factory = db_session_factory(engine)
        asset_id = f"durable-{uuid4().hex[:8]}"

        try:
            async with factory() as session:
                workspace_id = str(await seed_workspace(session, "prov-restart"))
                await ProvenanceTracker.record_provenance(
                    session,
                    asset_id,
                    "created",
                    "user-1",
                    {"source": "upload"},
                    workspace_id=workspace_id,
                )
                await ProvenanceTracker.record_provenance(
                    session, asset_id, "ai_generated", "user-2", workspace_id=workspace_id
                )
        finally:
            await engine.dispose()

        # Simulate the process going away and coming back.
        restarted_engine = await fresh_engine()
        restarted = db_session_factory(restarted_engine)
        try:
            async with restarted() as session:
                chain = await ProvenanceTracker.get_provenance_chain(session, asset_id)

            assert [e["action"] for e in chain] == ["created", "ai_generated"]
            assert chain[0]["details"] == {"source": "upload"}
            assert chain[0]["timestamp"] is not None
        finally:
            await restarted_engine.dispose()

    def test_lsb_watermark_roundtrip(self):
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        metadata = {"author": "test", "version": 1, "synthetic": False}
        watermarked = ProvenanceTracker.add_content_metadata(img, metadata)
        extracted = ProvenanceTracker.extract_content_metadata(watermarked)
        assert extracted is not None
        assert extracted["author"] == "test"
        assert extracted["version"] == 1

    def test_label_synthetic(self):
        img = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        labeled = ProvenanceTracker.label_synthetic(img, label="AI-GENERATED")
        # Should have invisible metadata
        meta = ProvenanceTracker.extract_content_metadata(labeled)
        assert meta is not None
        assert meta["synthetic"] is True

    def test_extract_returns_none_for_no_watermark(self):
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        result = ProvenanceTracker.extract_content_metadata(img)
        # May return None or empty depending on bit patterns
        # With all zeros, length = 0 → returns None
        assert result is None


# ---------------------------------------------------------------------------
# Compliance tests
# ---------------------------------------------------------------------------

class TestCompliance:
    def test_compliance_check_returns_status(self):
        result = ComplianceManager.check_compliance(None, "ws-1", "hipaa")
        assert "compliant" in result
        assert "checks" in result
        assert "score" in result
        assert isinstance(result["score"], float)

    def test_compliance_report(self):
        report = ComplianceManager.generate_compliance_report(None, "ws-1", "soc2")
        assert report["pack"] == "soc2"
        assert "overall" in report
        assert "checks" in report
        assert "recommendations" in report

    def test_legal_hold(self):
        hold = ComplianceManager.legal_hold(None, ["a1", "a2"], "litigation", "admin")
        assert hold["assets_held"] == 2
        assert "hold_id" in hold

        released = ComplianceManager.release_hold(None, hold["hold_id"])
        assert released["released"] == 2

    def test_unknown_pack_raises(self):
        with pytest.raises(ValueError, match="Unknown compliance pack"):
            ComplianceManager.check_compliance(None, "ws-1", "unknown_pack")

    def test_gdpr_check(self):
        result = ComplianceManager.check_compliance(None, "ws-1", "gdpr")
        assert "compliant" in result
        # GDPR has right_to_deletion which fails by default
        statuses = [c["status"] for c in result["checks"]]
        assert "fail" in statuses


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def api_client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_api_blur_plates(api_client):
    """POST /api/safety/blur-plates returns a base64 image."""
    import cv2
    img = _make_image_with_plate()
    _, buf = cv2.imencode(".png", img)
    resp = await api_client.post(
        "/api/safety/blur-plates",
        files={"file": ("plate.png", buf.tobytes(), "image/png")},
    )
    assert resp.status_code == 200
    assert "image" in resp.json()


@pytest.mark.anyio
async def test_api_anonymize_voice(api_client):
    """POST /api/safety/anonymize-voice returns base64 audio."""
    wav = _make_wav_bytes()
    resp = await api_client.post(
        "/api/safety/anonymize-voice",
        files={"file": ("voice.wav", wav, "audio/wav")},
        data={"method": "pitch"},
    )
    assert resp.status_code == 200
    assert "audio" in resp.json()


@pytest.mark.anyio
async def test_api_compliance(api_client):
    """GET /api/safety/compliance/hipaa returns compliance status."""
    resp = await api_client.get("/api/safety/compliance/hipaa")
    assert resp.status_code == 200
    body = resp.json()
    assert "compliant" in body
    assert "checks" in body


@pytest.mark.anyio
async def test_api_compliance_report(api_client):
    """POST /api/safety/compliance/soc2/report returns a report."""
    resp = await api_client.post("/api/safety/compliance/soc2/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pack"] == "soc2"


@pytest.mark.anyio
async def test_api_legal_hold(api_client):
    """POST /api/safety/legal-hold creates a hold."""
    resp = await api_client.post(
        "/api/safety/legal-hold",
        json={"asset_ids": ["a1"], "reason": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["assets_held"] == 1


@pytest.mark.anyio
async def test_api_provenance():
    """GET /api/safety/provenance/{asset_id} returns the recorded chain.

    The route takes its session from get_async_session, so that dependency is
    pointed at the test database — otherwise the endpoint reads the app's
    configured database and never sees the row this test wrote.
    """
    await requires_postgres()
    asset_id = f"test-asset-api-{uuid4().hex[:8]}"

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    from app.database import get_async_session
    from app.main import app

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    try:
        async with factory() as session:
            await ProvenanceTracker.record_provenance(
                session, asset_id, "created", "u1"
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(f"/api/safety/provenance/{asset_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["asset_id"] == asset_id
        assert [e["action"] for e in body["chain"]] == ["created"]
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()


@pytest.mark.anyio
async def test_api_policy_evaluate(api_client):
    """POST /api/safety/policy/evaluate returns evaluation."""
    resp = await api_client.post(
        "/api/safety/policy/evaluate",
        json={
            "scan_result": {"pii_found": [{"type": "email"}], "faces_detected": 0, "risk_score": 0.1},
            "policy_name": "strict_pii",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False
