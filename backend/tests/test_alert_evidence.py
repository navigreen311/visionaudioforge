"""Tests for auto-clip, evidence bundles, and chain-of-custody services.

Evidence bundles and custody records are database-backed, so these run against
a real server and skip when none is reachable (as in CI). The AutoClipService
tests touch only the filesystem and always run.
"""

import hashlib
import os
import tempfile
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db
from app.database import get_async_session
from app.main import app
from app.services.alerts.auto_clip import AutoClipService
from app.services.alerts.chain_of_custody import ChainOfCustodyService
from app.services.alerts.evidence_bundle import EvidenceBundleService
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def evidence_env():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "evidence")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
async def db(evidence_env):
    factory, _ = evidence_env
    async with factory() as session:
        yield session


@pytest.fixture
def workspace_id(evidence_env):
    return str(evidence_env[1])


@pytest.fixture
async def client(evidence_env):
    """HTTP client bound to the test database.

    The evidence routes take their session from get_async_session, so both
    dependencies are overridden.
    """
    factory, _ = evidence_env

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_async_session, None)


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
        assert f.read() == custom_frame

    os.remove(result["path"])


# ── EvidenceBundleService tests ──────────────────────────────────


@pytest.mark.anyio
async def test_create_evidence_bundle(db, alert_id, workspace_id):
    """A bundle records the alert it was built around."""
    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, case_id="CASE-1", workspace_id=workspace_id,
    )

    assert bundle["bundle_id"]
    assert bundle["metadata"]["alert_id"] == alert_id
    assert bundle["metadata"]["case_id"] == "CASE-1"
    assert bundle["clips"] == []


@pytest.mark.anyio
async def test_export_bundle_json(db, alert_id, workspace_id):
    """JSON export round-trips through the stored bundle."""
    import json

    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )
    exported = await EvidenceBundleService.export_bundle(
        db, bundle["bundle_id"], format="json",
    )

    payload = json.loads(exported.decode())
    assert payload["bundle_id"] == bundle["bundle_id"]
    assert payload["export_metadata"]["format"] == "json"


@pytest.mark.anyio
async def test_export_bundle_pdf_stub(db, alert_id, workspace_id):
    """The PDF stub export says what it is rather than pretending."""
    import json

    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )
    exported = await EvidenceBundleService.export_bundle(
        db, bundle["bundle_id"], format="pdf_stub",
    )

    payload = json.loads(exported.decode())
    assert payload["export_metadata"]["format"] == "pdf_stub"
    assert "reportlab" in payload["export_metadata"]["note"]


@pytest.mark.anyio
async def test_export_bundle_not_found(db):
    with pytest.raises(ValueError, match="not found"):
        await EvidenceBundleService.export_bundle(db, str(uuid.uuid4()))


@pytest.mark.anyio
async def test_export_bundle_rejects_unknown_format(db, alert_id, workspace_id):
    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )
    with pytest.raises(ValueError, match="Unsupported export format"):
        await EvidenceBundleService.export_bundle(
            db, bundle["bundle_id"], format="docx"
        )


@pytest.mark.anyio
async def test_add_to_bundle(db, alert_id, asset_id, workspace_id):
    """Assets land in the bucket matching their type."""
    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )

    await EvidenceBundleService.add_to_bundle(
        db, bundle["bundle_id"], asset_id, asset_type="clip",
    )
    updated = await EvidenceBundleService.add_to_bundle(
        db, bundle["bundle_id"], str(uuid.uuid4()), asset_type="snapshot",
    )

    assert [c["asset_id"] for c in updated["clips"]] == [asset_id]
    assert len(updated["snapshots"]) == 1
    assert updated["events"] == []


@pytest.mark.anyio
async def test_add_to_unknown_bundle_raises(db, asset_id):
    with pytest.raises(ValueError, match="not found"):
        await EvidenceBundleService.add_to_bundle(db, str(uuid.uuid4()), asset_id)


@pytest.mark.anyio
async def test_list_bundles_is_workspace_scoped(evidence_env, db, alert_id, workspace_id):
    """Bundles from another workspace must not be listed.

    The in-memory store had no workspace to filter on and returned every
    bundle to every caller.
    """
    factory, _ = evidence_env

    await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )

    async with factory() as other_session:
        other_ws = str(await seed_workspace(other_session, "evidence-other"))
        await EvidenceBundleService.create_bundle(
            other_session, str(uuid.uuid4()), workspace_id=other_ws
        )

    bundles = await EvidenceBundleService.list_bundles(db, workspace_id)
    assert [b["alert_id"] for b in bundles] == [alert_id]


@pytest.mark.anyio
async def test_list_bundles_counts_items(db, alert_id, workspace_id):
    bundle = await EvidenceBundleService.create_bundle(
        db, alert_id, workspace_id=workspace_id
    )
    await EvidenceBundleService.add_to_bundle(
        db, bundle["bundle_id"], str(uuid.uuid4()), asset_type="clip"
    )
    await EvidenceBundleService.add_to_bundle(
        db, bundle["bundle_id"], str(uuid.uuid4()), asset_type="event"
    )

    summary = (await EvidenceBundleService.list_bundles(db, workspace_id))[0]
    assert summary["clip_count"] == 1
    assert summary["event_count"] == 1
    assert summary["snapshot_count"] == 0


# ── ChainOfCustodyService tests ──────────────────────────────────


@pytest.mark.anyio
async def test_chain_of_custody_logs_access(db, asset_id, user_id, workspace_id):
    record = await ChainOfCustodyService.log_access(
        db, asset_id, user_id, "viewed", workspace_id=workspace_id,
    )

    assert record["asset_id"] == asset_id
    assert record["action"] == "viewed"
    assert record["timestamp"]


@pytest.mark.anyio
async def test_chain_of_custody_invalid_action(db, asset_id, user_id):
    with pytest.raises(ValueError, match="Invalid custody action"):
        await ChainOfCustodyService.log_access(db, asset_id, user_id, "teleported")


@pytest.mark.anyio
async def test_custody_chain_ordered(db, asset_id, user_id, workspace_id):
    """The chain reads back in the order the accesses happened."""
    for action in ("viewed", "downloaded", "exported"):
        await ChainOfCustodyService.log_access(
            db, asset_id, user_id, action, workspace_id=workspace_id,
        )

    chain = await ChainOfCustodyService.get_custody_chain(db, asset_id)

    assert [entry["action"] for entry in chain] == [
        "viewed",
        "downloaded",
        "exported",
    ]
    assert chain[0]["timestamp"] <= chain[1]["timestamp"] <= chain[2]["timestamp"]


@pytest.mark.anyio
async def test_custody_chain_is_per_asset(db, user_id, workspace_id):
    """One asset's accesses never appear in another's chain."""
    asset_a, asset_b = str(uuid.uuid4()), str(uuid.uuid4())

    await ChainOfCustodyService.log_access(
        db, asset_a, user_id, "viewed", workspace_id=workspace_id
    )
    await ChainOfCustodyService.log_access(
        db, asset_b, user_id, "deleted", workspace_id=workspace_id
    )

    assert [e["action"] for e in await ChainOfCustodyService.get_custody_chain(db, asset_a)] == ["viewed"]
    assert [e["action"] for e in await ChainOfCustodyService.get_custody_chain(db, asset_b)] == ["deleted"]


@pytest.mark.anyio
async def test_custody_write_failure_is_not_swallowed(db, asset_id, workspace_id):
    """A custody event that cannot be stored must raise, not vanish.

    The previous implementation wrapped its database write in a bare except
    and kept going, so a failed write left no trace anywhere.
    """
    over_long_asset_id = "x" * 200  # asset_id is String(64)

    with pytest.raises(Exception):
        await ChainOfCustodyService.log_access(
            db, over_long_asset_id, str(uuid.uuid4()), "viewed",
            workspace_id=workspace_id,
        )


@pytest.mark.anyio
async def test_verify_integrity_hash(db, workspace_id):
    """Integrity verification computes SHA-256 and detects changes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"evidence data content")
        file_path = f.name

    try:
        original_hash = hashlib.sha256(b"evidence data content").hexdigest()
        result = await ChainOfCustodyService.verify_integrity(
            db, "test-asset", original_hash=original_hash, file_path=file_path,
        )
        assert result["intact"] is True
        assert result["hash"] == original_hash

        with open(file_path, "wb") as f:
            f.write(b"tampered data")

        tampered = await ChainOfCustodyService.verify_integrity(
            db, "test-asset", original_hash=original_hash, file_path=file_path,
        )
        assert tampered["intact"] is False
        assert tampered["hash"] != original_hash
    finally:
        os.remove(file_path)


@pytest.mark.anyio
async def test_integrity_baseline_is_recorded_then_compared(db, workspace_id):
    """The first hash becomes the baseline; a later change is caught."""
    asset = f"baseline-{uuid.uuid4().hex[:8]}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"original content")
        file_path = f.name

    try:
        first = await ChainOfCustodyService.verify_integrity(
            db, asset, file_path=file_path, workspace_id=workspace_id,
        )
        assert first["intact"] is True
        assert first["note"] == "Initial hash recorded"

        # Unchanged file still matches the stored baseline.
        again = await ChainOfCustodyService.verify_integrity(
            db, asset, file_path=file_path, workspace_id=workspace_id,
        )
        assert again["intact"] is True
        assert again["note"] == "Hash matches stored record"

        with open(file_path, "wb") as f:
            f.write(b"tampered content")

        tampered = await ChainOfCustodyService.verify_integrity(
            db, asset, file_path=file_path, workspace_id=workspace_id,
        )
        assert tampered["intact"] is False
        assert "modified" in tampered["note"]
    finally:
        os.remove(file_path)


@pytest.mark.anyio
async def test_verify_integrity_missing_file(db):
    result = await ChainOfCustodyService.verify_integrity(
        db, "missing-asset", file_path="/nonexistent/path/file.bin",
    )
    assert result["intact"] is False
    assert "not found" in result["note"].lower()


@pytest.mark.anyio
async def test_custody_report(db, asset_id, user_id, workspace_id):
    """The report aggregates chain, integrity and access stats."""
    await ChainOfCustodyService.log_access(
        db, asset_id, user_id, "viewed", workspace_id=workspace_id,
    )
    await ChainOfCustodyService.log_access(
        db, asset_id, str(uuid.uuid4()), "downloaded", workspace_id=workspace_id,
    )

    report = await ChainOfCustodyService.generate_custody_report(db, asset_id)

    assert report["asset_id"] == asset_id
    assert report["access_count"] == 2
    assert report["unique_users"] == 2
    assert len(report["chain"]) == 2
    assert "intact" in report["integrity"]


# ── Durability ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_evidence_survives_a_restart(evidence_env):
    """Bundles, custody chains and integrity baselines outlive the process.

    This is the whole point of the change: an evidence trail that reports a
    complete history only until the next deploy is worse than no trail at all,
    because it looks authoritative while being empty.
    """
    factory, workspace = evidence_env
    workspace_id = str(workspace)

    alert = str(uuid.uuid4())
    asset = f"durable-{uuid.uuid4().hex[:8]}"
    actor = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"sealed evidence")
        file_path = f.name

    try:
        async with factory() as session:
            bundle = await EvidenceBundleService.create_bundle(
                session, alert, case_id="CASE-9", workspace_id=workspace_id,
            )
            await EvidenceBundleService.add_to_bundle(
                session, bundle["bundle_id"], asset, asset_type="clip",
            )
            await ChainOfCustodyService.log_access(
                session, asset, actor, "viewed", workspace_id=workspace_id,
            )
            await ChainOfCustodyService.log_access(
                session, asset, actor, "exported", workspace_id=workspace_id,
            )
            await ChainOfCustodyService.verify_integrity(
                session, asset, file_path=file_path, workspace_id=workspace_id,
            )

        restarted_engine = await fresh_engine()
        restarted = db_session_factory(restarted_engine)

        try:
            async with restarted() as session:
                stored = await EvidenceBundleService.get_bundle(
                    session, bundle["bundle_id"]
                )
                assert stored["metadata"]["case_id"] == "CASE-9"
                assert [c["asset_id"] for c in stored["clips"]] == [asset]

                chain = await ChainOfCustodyService.get_custody_chain(session, asset)
                assert [e["action"] for e in chain] == ["viewed", "exported"]

                listed = await EvidenceBundleService.list_bundles(
                    session, workspace_id
                )
                assert [b["bundle_id"] for b in listed] == [bundle["bundle_id"]]

                # The baseline survived, so tampering is still detectable.
                with open(file_path, "wb") as f:
                    f.write(b"tampered after restart")

                verdict = await ChainOfCustodyService.verify_integrity(
                    session, asset, file_path=file_path,
                )
                assert verdict["intact"] is False
        finally:
            await restarted_engine.dispose()
    finally:
        os.remove(file_path)


# ── API route tests ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_api_auto_clip(client):
    """POST /api/alerts/{id}/auto-clip should return clip + snapshot."""
    resp = await client.post(
        f"/api/alerts/{uuid.uuid4()}/auto-clip",
        params={"before_s": 5, "after_s": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["clip"]["duration_s"] == 8.0
    assert data["clip"]["type"] == "video"
    assert data["snapshot"]["type"] == "image"

    for path in (data["clip"]["path"], data["snapshot"]["path"]):
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.anyio
async def test_api_bundle(client, workspace_id):
    """POST /api/alerts/{id}/bundle should create an evidence bundle."""
    alert = str(uuid.uuid4())
    resp = await client.post(
        f"/api/alerts/{alert}/bundle",
        params={"case_id": "CASE-100", "workspace_id": workspace_id},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["bundle_id"]
    assert data["metadata"]["case_id"] == "CASE-100"
    assert data["metadata"]["alert_id"] == alert


@pytest.mark.anyio
async def test_api_list_and_export_bundles(client, workspace_id):
    """A created bundle is listable and exportable over HTTP."""
    created = await client.post(
        f"/api/alerts/{uuid.uuid4()}/bundle",
        params={"workspace_id": workspace_id},
    )
    bundle_id = created.json()["bundle_id"]

    listed = await client.get("/api/alerts/bundles", params={"workspace_id": workspace_id})
    assert listed.status_code == 200
    assert [b["bundle_id"] for b in listed.json()] == [bundle_id]

    exported = await client.get(f"/api/alerts/bundles/{bundle_id}/export")
    assert exported.status_code == 200
    assert exported.json()["bundle_id"] == bundle_id


@pytest.mark.anyio
async def test_api_export_unknown_bundle_404s(client):
    resp = await client.get(f"/api/alerts/bundles/{uuid.uuid4()}/export")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_custody(client):
    """GET /api/alerts/{id}/custody should return a custody report."""
    alert = str(uuid.uuid4())
    resp = await client.get(f"/api/alerts/{alert}/custody")

    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == alert
    assert data["chain"] == []
    assert data["access_count"] == 0
    assert "intact" in data["integrity"]
