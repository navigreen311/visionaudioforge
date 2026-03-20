"""Tests for auto-clip, evidence bundles, and chain-of-custody services."""

import hashlib
import os
import tempfile
import uuid

import pytest

from app.services.alerts.auto_clip import AutoClipService
from app.services.alerts.evidence_bundle import EvidenceBundleService
from app.services.alerts.chain_of_custody import ChainOfCustodyService


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_stores():
    """Reset in-memory stores before each test."""
    EvidenceBundleService.clear_store()
    ChainOfCustodyService.clear_store()
    yield
    EvidenceBundleService.clear_store()
    ChainOfCustodyService.clear_store()


@pytest.fixture
def alert_id():
    return str(uuid.uuid4())


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def asset_id():
    return str(uuid.uuid4())


# ── AutoClipService tests ────────────────────────────────────────


@pytest.mark.anyio
async def test_auto_clip_creates_asset(alert_id):
    """Auto-clip should create a clip file and return metadata."""
    result = await AutoClipService.capture_clip_on_alert(
        alert_id=alert_id, before_s=10, after_s=5,
    )

    assert result["clip_id"]
    assert result["asset_id"]
    assert result["duration_s"] == 15.0
    assert result["path"].endswith(".avi")
    assert result["sha256"]
    assert result["type"] == "video"
    assert os.path.exists(result["path"])

    # Clean up
    os.remove(result["path"])


@pytest.mark.anyio
async def test_auto_snapshot_creates_asset(alert_id):
    """Snapshot should create a PNG file and return metadata."""
    result = await AutoClipService.create_snapshot_on_alert(alert_id=alert_id)

    assert result["snapshot_id"]
    assert result["asset_id"]
    assert result["path"].endswith(".png")
    assert result["sha256"]
    assert result["type"] == "image"
    assert os.path.exists(result["path"])

    # Clean up
    os.remove(result["path"])


@pytest.mark.anyio
async def test_auto_snapshot_with_custom_frame(alert_id):
    """Snapshot should use provided frame bytes if given."""
    custom_frame = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    result = await AutoClipService.create_snapshot_on_alert(
        alert_id=alert_id, frame=custom_frame,
    )

    assert os.path.exists(result["path"])
    with open(result["path"], "rb") as f:
        content = f.read()
    assert content == custom_frame

    os.remove(result["path"])


# ── EvidenceBundleService tests ──────────────────────────────────


@pytest.mark.anyio
async def test_create_evidence_bundle(alert_id):
    """Creating a bundle should return structured bundle data."""
    bundle = await EvidenceBundleService.create_bundle(
        db=None, alert_id=alert_id, case_id="CASE-001",
    )

    assert bundle["bundle_id"]
    assert bundle["alert"]["alert_id"] == alert_id
    assert isinstance(bundle["clips"], list)
    assert isinstance(bundle["snapshots"], list)
    assert isinstance(bundle["events"], list)
    assert bundle["metadata"]["case_id"] == "CASE-001"
    assert bundle["metadata"]["version"] == "1.0"


@pytest.mark.anyio
async def test_export_bundle_json(alert_id):
    """Exporting as JSON should return valid UTF-8 bytes."""
    import json

    bundle = await EvidenceBundleService.create_bundle(db=None, alert_id=alert_id)
    exported = await EvidenceBundleService.export_bundle(
        db=None, bundle_id=bundle["bundle_id"], format="json",
    )

    assert isinstance(exported, bytes)
    data = json.loads(exported.decode("utf-8"))
    assert data["bundle_id"] == bundle["bundle_id"]
    assert "export_metadata" in data
    assert data["export_metadata"]["format"] == "json"


@pytest.mark.anyio
async def test_export_bundle_pdf_stub(alert_id):
    """PDF stub export should note that reportlab is required."""
    import json

    bundle = await EvidenceBundleService.create_bundle(db=None, alert_id=alert_id)
    exported = await EvidenceBundleService.export_bundle(
        db=None, bundle_id=bundle["bundle_id"], format="pdf_stub",
    )

    data = json.loads(exported.decode("utf-8"))
    assert "reportlab" in data["export_metadata"]["note"].lower()


@pytest.mark.anyio
async def test_export_bundle_not_found():
    """Exporting a non-existent bundle should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await EvidenceBundleService.export_bundle(
            db=None, bundle_id="nonexistent-id",
        )


@pytest.mark.anyio
async def test_add_to_bundle(alert_id, asset_id):
    """Adding an asset to a bundle should update the bundle."""
    bundle = await EvidenceBundleService.create_bundle(db=None, alert_id=alert_id)
    assert len(bundle["clips"]) == 0

    updated = await EvidenceBundleService.add_to_bundle(
        db=None, bundle_id=bundle["bundle_id"], asset_id=asset_id, asset_type="clip",
    )

    assert len(updated["clips"]) == 1
    assert updated["clips"][0]["asset_id"] == asset_id


@pytest.mark.anyio
async def test_list_bundles(alert_id):
    """Listing bundles should include created bundles."""
    await EvidenceBundleService.create_bundle(db=None, alert_id=alert_id)
    await EvidenceBundleService.create_bundle(db=None, alert_id=str(uuid.uuid4()))

    bundles = await EvidenceBundleService.list_bundles(db=None, workspace_id="")
    assert len(bundles) == 2
    assert all("bundle_id" in b for b in bundles)


# ── ChainOfCustodyService tests ─────────────────────────────────


@pytest.mark.anyio
async def test_chain_of_custody_logs_access(asset_id, user_id):
    """Logging access should create a custody record."""
    record = await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user_id,
        action="viewed", details="Viewed from dashboard",
    )

    assert record["asset_id"] == asset_id
    assert record["user_id"] == user_id
    assert record["action"] == "viewed"
    assert record["details"] == "Viewed from dashboard"
    assert record["timestamp"]


@pytest.mark.anyio
async def test_chain_of_custody_invalid_action(asset_id, user_id):
    """Invalid custody actions should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid custody action"):
        await ChainOfCustodyService.log_access(
            db=None, asset_id=asset_id, user_id=user_id, action="hacked",
        )


@pytest.mark.anyio
async def test_custody_chain_ordered(asset_id, user_id):
    """Custody chain should be returned in chronological order."""
    import asyncio

    await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user_id, action="viewed",
    )
    await asyncio.sleep(0.01)  # Ensure different timestamps
    await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user_id, action="downloaded",
    )
    await asyncio.sleep(0.01)
    await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user_id, action="exported",
    )

    chain = await ChainOfCustodyService.get_custody_chain(db=None, asset_id=asset_id)
    assert len(chain) == 3
    assert chain[0]["action"] == "viewed"
    assert chain[1]["action"] == "downloaded"
    assert chain[2]["action"] == "exported"
    # Verify chronological order
    assert chain[0]["timestamp"] <= chain[1]["timestamp"] <= chain[2]["timestamp"]


@pytest.mark.anyio
async def test_verify_integrity_hash():
    """Integrity verification should compute SHA-256 and detect changes."""
    # Create a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"evidence data content")
        file_path = f.name

    try:
        original_hash = hashlib.sha256(b"evidence data content").hexdigest()
        result = await ChainOfCustodyService.verify_integrity(
            db=None, asset_id="test-asset",
            original_hash=original_hash, file_path=file_path,
        )
        assert result["intact"] is True
        assert result["hash"] == original_hash

        # Modify file and check again
        with open(file_path, "wb") as f:
            f.write(b"tampered data")

        result2 = await ChainOfCustodyService.verify_integrity(
            db=None, asset_id="test-asset",
            original_hash=original_hash, file_path=file_path,
        )
        assert result2["intact"] is False
        assert result2["hash"] != original_hash
    finally:
        os.remove(file_path)


@pytest.mark.anyio
async def test_verify_integrity_missing_file():
    """Integrity check on a missing file should return intact=False."""
    result = await ChainOfCustodyService.verify_integrity(
        db=None, asset_id="missing-asset",
        file_path="/nonexistent/path/file.bin",
    )
    assert result["intact"] is False
    assert "not found" in result["note"].lower()


@pytest.mark.anyio
async def test_custody_report(asset_id, user_id):
    """Custody report should aggregate chain, integrity, and access stats."""
    await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user_id, action="viewed",
    )
    user2 = str(uuid.uuid4())
    await ChainOfCustodyService.log_access(
        db=None, asset_id=asset_id, user_id=user2, action="downloaded",
    )

    report = await ChainOfCustodyService.generate_custody_report(
        db=None, asset_id=asset_id,
    )

    assert report["asset_id"] == asset_id
    assert report["access_count"] == 2
    assert report["unique_users"] == 2
    assert len(report["chain"]) == 2
    assert "intact" in report["integrity"]


# ── API route tests ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_api_auto_clip(client):
    """POST /api/alerts/{id}/auto-clip should return clip + snapshot."""
    fake_alert_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/alerts/{fake_alert_id}/auto-clip",
        params={"before_s": 5, "after_s": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "clip" in data
    assert "snapshot" in data
    assert data["clip"]["duration_s"] == 8.0
    assert data["clip"]["type"] == "video"
    assert data["snapshot"]["type"] == "image"

    # Clean up generated files
    for path in [data["clip"]["path"], data["snapshot"]["path"]]:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.anyio
async def test_api_bundle(client):
    """POST /api/alerts/{id}/bundle should create an evidence bundle."""
    fake_alert_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/alerts/{fake_alert_id}/bundle",
        params={"case_id": "CASE-100"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bundle_id"]
    assert data["metadata"]["case_id"] == "CASE-100"
    assert data["metadata"]["alert_id"] == fake_alert_id


@pytest.mark.anyio
async def test_api_custody(client):
    """GET /api/alerts/{id}/custody should return custody report."""
    fake_alert_id = str(uuid.uuid4())
    resp = await client.get(f"/api/alerts/{fake_alert_id}/custody")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == fake_alert_id
    assert "chain" in data
    assert "integrity" in data
    assert "access_count" in data
    assert "unique_users" in data
