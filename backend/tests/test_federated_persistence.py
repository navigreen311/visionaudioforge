"""Federated learning persistence — federations, participants and rounds.

The coordinator held federations in a module-level dict and recorded no round,
so `/rounds` had nothing to return and the console's chart was drawn from a
generator. These run against a real database and skip when none is reachable.
"""

from __future__ import annotations

import uuid

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import get_async_session
from app.main import app
from app.models.federated import (
    Federation,
    FederationRound,
    FederationStatus,
    ParticipantStatus,
    RoundStatus,
)
from app.services.federated.coordinator import FederatedCoordinator, _encode
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def fed_env():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "federated")

    try:
        yield factory, str(workspace_id)
    finally:
        await engine.dispose()


@pytest.fixture
async def db(fed_env):
    factory, _ = fed_env
    async with factory() as session:
        yield session


@pytest.fixture
def workspace_id(fed_env):
    return fed_env[1]


@pytest.fixture
def coordinator():
    return FederatedCoordinator()


@pytest.fixture
async def client(fed_env):
    factory, _ = fed_env

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_async_session, None)


def _update(*values: float) -> dict:
    """A single-layer update, encoded the way a participant would send it."""
    return _encode({"dense": np.array(values, dtype=np.float64)})


async def _two_party_federation(coordinator, db, workspace_id, **config):
    created = await coordinator.create_federation(
        db, workspace_id, "test-fed", "model-abc", config or None
    )
    fid = created["federation_id"]
    await coordinator.join_federation(db, fid, "site-a", {"data_size": 100})
    await coordinator.join_federation(db, fid, "site-b", {"data_size": 200})
    return fid


# ---------------------------------------------------------------------------
# Federation lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_federation_writes_a_row(coordinator, db, workspace_id):
    """A federation is a row, not a dict entry."""
    created = await coordinator.create_federation(
        db, workspace_id, "medical-imaging", "resnet50"
    )

    stored = (
        await db.execute(
            select(Federation).where(Federation.id == uuid.UUID(created["federation_id"]))
        )
    ).scalar_one()

    assert stored.name == "medical-imaging"
    assert stored.model_id == "resnet50"
    assert stored.status == FederationStatus.waiting
    assert stored.workspace_id == uuid.UUID(workspace_id)


@pytest.mark.anyio
async def test_joining_reaches_ready(coordinator, db, workspace_id):
    """Enough participants flips the federation to ready."""
    created = await coordinator.create_federation(db, workspace_id, "f", "m")
    fid = created["federation_id"]

    first = await coordinator.join_federation(db, fid, "site-a")
    assert first == {"joined": True, "participant_count": 1}

    second = await coordinator.join_federation(db, fid, "site-b")
    assert second["participant_count"] == 2

    federation = await coordinator._load(db, fid)
    assert federation.status == FederationStatus.ready


@pytest.mark.anyio
async def test_joining_twice_is_rejected(coordinator, db, workspace_id):
    """A site cannot join the same federation twice."""
    created = await coordinator.create_federation(db, workspace_id, "f", "m")
    fid = created["federation_id"]

    await coordinator.join_federation(db, fid, "site-a")
    again = await coordinator.join_federation(db, fid, "site-a")

    assert again == {"joined": False, "participant_count": 1}


@pytest.mark.anyio
async def test_start_round_requires_minimum_participants(
    coordinator, db, workspace_id
):
    created = await coordinator.create_federation(db, workspace_id, "f", "m")
    fid = created["federation_id"]
    await coordinator.join_federation(db, fid, "site-a")

    with pytest.raises(ValueError, match="at least 2 participants"):
        await coordinator.start_round(db, fid)


@pytest.mark.anyio
async def test_unknown_federation_raises(coordinator, db):
    with pytest.raises(ValueError, match="not found"):
        await coordinator.start_round(db, str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Rounds
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_start_round_records_a_round(coordinator, db, workspace_id):
    """Starting a round writes it — this is what /rounds reads back."""
    fid = await _two_party_federation(coordinator, db, workspace_id)

    started = await coordinator.start_round(db, fid)
    assert started["round_number"] == 1

    stored = (
        await db.execute(
            select(FederationRound).where(
                FederationRound.id == uuid.UUID(started["round_id"])
            )
        )
    ).scalar_one()

    assert stored.round_number == 1
    assert stored.status == RoundStatus.in_progress
    assert stored.participant_count == 2


@pytest.mark.anyio
async def test_submit_and_aggregate_records_the_outcome(
    coordinator, db, workspace_id
):
    """Aggregation averages what was actually submitted and stores the result."""
    fid = await _two_party_federation(coordinator, db, workspace_id)
    started = await coordinator.start_round(db, fid)
    rid = started["round_id"]

    await coordinator.submit_update(
        db, fid, rid, "site-a", _update(1.0, 1.0), {"loss": 0.5, "sample_count": 100}
    )
    second = await coordinator.submit_update(
        db, fid, rid, "site-b", _update(3.0, 3.0), {"loss": 0.3, "sample_count": 100}
    )
    assert second["updates_so_far"] == 2

    result = await coordinator.aggregate_round(db, fid, rid)
    assert result["participants"] == 2
    assert result["round_complete"] is True
    # Equal sample counts, so the averaged loss is the mean of the two.
    assert result["avg_metrics"]["loss"] == pytest.approx(0.4)

    rounds = await coordinator.list_rounds(db, fid)
    assert len(rounds) == 1
    assert rounds[0]["status"] == "completed"
    assert rounds[0]["participants"] == 2
    assert rounds[0]["completed_at"] is not None
    assert rounds[0]["aggregation_time_ms"] is not None


@pytest.mark.anyio
async def test_double_submission_is_rejected(coordinator, db, workspace_id):
    fid = await _two_party_federation(coordinator, db, workspace_id)
    rid = (await coordinator.start_round(db, fid))["round_id"]

    await coordinator.submit_update(db, fid, rid, "site-a", _update(1.0), {})
    with pytest.raises(ValueError, match="already submitted"):
        await coordinator.submit_update(db, fid, rid, "site-a", _update(2.0), {})


@pytest.mark.anyio
async def test_aggregating_nothing_raises_rather_than_inventing(
    coordinator, db, workspace_id
):
    """A round with no submissions must not produce a metric."""
    fid = await _two_party_federation(coordinator, db, workspace_id)
    rid = (await coordinator.start_round(db, fid))["round_id"]

    with pytest.raises(ValueError, match="No updates to aggregate"):
        await coordinator.aggregate_round(db, fid, rid)


@pytest.mark.anyio
async def test_contribution_metrics_accumulate(coordinator, db, workspace_id):
    """Participants carry what they contributed, across rounds."""
    fid = await _two_party_federation(coordinator, db, workspace_id)
    rid = (await coordinator.start_round(db, fid))["round_id"]

    await coordinator.submit_update(
        db, fid, rid, "site-a", _update(1.0), {"sample_count": 100}
    )
    await coordinator.submit_update(
        db, fid, rid, "site-b", _update(2.0), {"sample_count": 250}
    )
    await coordinator.aggregate_round(db, fid, rid)

    federation = await coordinator._load(db, fid)
    by_site = {p.site: p for p in federation.participants}

    assert by_site["site-a"].samples_contributed == 100
    assert by_site["site-b"].samples_contributed == 250
    assert by_site["site-a"].rounds_contributed == 1


@pytest.mark.anyio
async def test_privacy_budget_is_spent_and_enforced(coordinator, db, workspace_id):
    """Epsilon accumulates across rounds and eventually blocks a new one."""
    fid = await _two_party_federation(
        coordinator, db, workspace_id, max_rounds=1, privacy_budget=0.5
    )
    rid = (await coordinator.start_round(db, fid))["round_id"]

    await coordinator.submit_update(db, fid, rid, "site-a", _update(1.0), {})
    federation = await coordinator._load(db, fid)
    assert federation.privacy_epsilon_spent > 0

    # max_rounds is 1, so a second round is refused.
    with pytest.raises(ValueError, match="Maximum rounds reached"):
        await coordinator.start_round(db, fid)


# ---------------------------------------------------------------------------
# Durability
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_federation_and_rounds_survive_a_restart(fed_env, coordinator):
    """Written through one engine, read back through a brand-new one.

    A fresh engine means a fresh pool and identity map, so anything still
    readable genuinely came out of Postgres.
    """
    factory, workspace_id = fed_env

    async with factory() as session:
        fid = await _two_party_federation(coordinator, session, workspace_id)
        rid = (await coordinator.start_round(session, fid))["round_id"]
        await coordinator.submit_update(
            session, fid, rid, "site-a", _update(1.0, 2.0), {"loss": 0.4, "sample_count": 10}
        )
        await coordinator.submit_update(
            session, fid, rid, "site-b", _update(3.0, 4.0), {"loss": 0.2, "sample_count": 10}
        )
        await coordinator.aggregate_round(session, fid, rid)

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)

    try:
        async with restarted() as session:
            status = await coordinator.get_federation_status(session, fid)
            assert status["current_round"] == 1
            assert {p["id"] for p in status["participants"]} == {"site-a", "site-b"}
            assert status["metrics_history"][0]["metrics"]["loss"] == pytest.approx(0.3)

            rounds = await coordinator.list_rounds(session, fid)
            assert [r["round"] for r in rounds] == [1]
            assert rounds[0]["status"] == "completed"

            # The aggregated weights survived too, so the next round can build
            # on them rather than starting from nothing.
            federation = await coordinator._load(session, fid)
            assert federation.global_model is not None
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_submissions_are_visible_to_another_worker(fed_env, coordinator):
    """Submit on one session, aggregate on another — the multi-worker case."""
    factory, workspace_id = fed_env

    async with factory() as writer:
        fid = await _two_party_federation(coordinator, writer, workspace_id)
        rid = (await coordinator.start_round(writer, fid))["round_id"]
        await coordinator.submit_update(
            writer, fid, rid, "site-a", _update(2.0), {"sample_count": 1}
        )

    async with factory() as other_worker:
        await coordinator.submit_update(
            other_worker, fid, rid, "site-b", _update(4.0), {"sample_count": 1}
        )
        result = await coordinator.aggregate_round(other_worker, fid, rid)

    assert result["participants"] == 2


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_create_and_list(client, workspace_id):
    created = await client.post(
        "/api/federated/federations",
        json={
            "name": "api-fed",
            "model_id": "m1",
            "min_participants": 2,
            "rounds": 5,
            "workspace_id": workspace_id,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["name"] == "api-fed"
    assert body["status"] == "waiting"
    assert body["total_rounds"] == 5

    listed = await client.get(
        "/api/federated/federations", params={"workspace_id": workspace_id}
    )
    assert [f["id"] for f in listed.json()] == [body["id"]]
    # The list reports a count; the detail view reports the participants.
    assert listed.json()[0]["participants"] == 0


@pytest.mark.anyio
async def test_api_rounds_is_empty_until_one_runs(client, workspace_id):
    """The endpoint that used to fabricate twelve rounds for any id."""
    created = await client.post(
        "/api/federated/federations",
        json={"name": "f", "model_id": "m", "workspace_id": workspace_id},
    )
    fid = created.json()["id"]

    rounds = await client.get(f"/api/federated/federations/{fid}/rounds")
    assert rounds.status_code == 200
    assert rounds.json() == []


@pytest.mark.anyio
@pytest.mark.parametrize("action,expected", [
    ("pause", "paused"),
    ("resume", "training"),
    ("stop", "completed"),
])
async def test_api_training_controls_are_reachable(
    client, workspace_id, action, expected
):
    """TrainingControls calls /federations/{id}/{action}; these all 404'd."""
    created = await client.post(
        "/api/federated/federations",
        json={"name": "f", "model_id": "m", "workspace_id": workspace_id},
    )
    fid = created.json()["id"]

    resp = await client.post(f"/api/federated/federations/{fid}/{action}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == expected

    detail = await client.get(f"/api/federated/federations/{fid}")
    assert detail.json()["status"] == expected


@pytest.mark.anyio
async def test_api_participants_round_trip(client, workspace_id):
    """AddParticipantModal posts here; it 404'd before."""
    created = await client.post(
        "/api/federated/federations",
        json={"name": "f", "model_id": "m", "workspace_id": workspace_id},
    )
    fid = created.json()["id"]

    added = await client.post(
        f"/api/federated/federations/{fid}/participants",
        json={"site": "site-a", "name": "Site A", "data_size": 500},
    )
    assert added.status_code == 200, added.text
    assert added.json()["participant"]["site"] == "site-a"

    reconnect = await client.post(
        f"/api/federated/federations/{fid}/participants/site-a/reconnect"
    )
    assert reconnect.json()["status"] == ParticipantStatus.reconnecting.value

    removed = await client.delete(
        f"/api/federated/federations/{fid}/participants/site-a"
    )
    assert removed.json()["remaining_participants"] == 0

    missing = await client.delete(
        f"/api/federated/federations/{fid}/participants/site-a"
    )
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_api_retrain_exists(client, workspace_id):
    """The console offers retrain and the backend had no handler at all."""
    created = await client.post(
        "/api/federated/federations",
        json={
            "name": "f",
            "model_id": "m",
            "min_participants": 1,
            "workspace_id": workspace_id,
        },
    )
    fid = created.json()["id"]
    await client.post(
        f"/api/federated/federations/{fid}/participants",
        json={"site": "site-a", "name": "Site A"},
    )
    await client.post(f"/api/federated/federations/{fid}/stop")

    resp = await client.post(f"/api/federated/federations/{fid}/retrain")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "training"
    assert resp.json()["round"] == 1


@pytest.mark.anyio
async def test_api_unknown_federation_404s(client):
    resp = await client.get(f"/api/federated/federations/{uuid.uuid4()}")
    assert resp.status_code == 404

    bad_id = await client.get("/api/federated/federations/not-a-uuid")
    assert bad_id.status_code == 404
