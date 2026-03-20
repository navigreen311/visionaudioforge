"""Tests for the Federated Learning framework — coordinator, aggregation, privacy."""

import base64
import io
import math
import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.services.federated.aggregation import FederatedAggregator
from app.services.federated.coordinator import FederatedCoordinator
from app.services.federated.privacy import DifferentialPrivacy
from app.services.federated.secure_aggregation import SecureAggregation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001"
MODEL_ID = "model-abc-123"


def _make_update(*values: float) -> dict:
    """Create a simple single-layer model update."""
    return {"dense": np.array(values, dtype=np.float64)}


def _serialize_update(update: dict) -> dict:
    """Encode numpy arrays to base64 for transport."""
    out = {}
    for k, v in update.items():
        buf = io.BytesIO()
        np.save(buf, v)
        out[k] = base64.b64encode(buf.getvalue()).decode()
    return out


# ---------------------------------------------------------------------------
# Federation lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def coordinator():
    return FederatedCoordinator()


@pytest.fixture
def db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_federation(coordinator, db):
    result = await coordinator.create_federation(db, WORKSPACE_ID, "test-fed", MODEL_ID)
    assert result["name"] == "test-fed"
    assert result["status"] == "created"
    assert result["federation_id"]
    assert result["config"]["min_participants"] == 2
    assert result["config"]["aggregation_method"] == "fedavg"


@pytest.mark.asyncio
async def test_join_federation(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "test-fed", MODEL_ID)
    fid = fed["federation_id"]

    r1 = await coordinator.join_federation(db, fid, "participant-a", {"org": "A"})
    assert r1["joined"] is True
    assert r1["participant_count"] == 1

    r2 = await coordinator.join_federation(db, fid, "participant-b", {"org": "B"})
    assert r2["joined"] is True
    assert r2["participant_count"] == 2

    # Duplicate join should fail
    r3 = await coordinator.join_federation(db, fid, "participant-a")
    assert r3["joined"] is False
    assert r3["participant_count"] == 2


@pytest.mark.asyncio
async def test_start_round(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "test-fed", MODEL_ID)
    fid = fed["federation_id"]
    await coordinator.join_federation(db, fid, "p1")
    await coordinator.join_federation(db, fid, "p2")

    result = await coordinator.start_round(db, fid)
    assert result["round_number"] == 1
    assert result["round_id"]
    assert result["global_model_version"] == "v1"
    assert result["instructions"]["action"] == "train_local_model"


@pytest.mark.asyncio
async def test_start_round_insufficient_participants(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "test-fed", MODEL_ID)
    fid = fed["federation_id"]
    await coordinator.join_federation(db, fid, "p1")

    with pytest.raises(ValueError, match="Need at least"):
        await coordinator.start_round(db, fid)


@pytest.mark.asyncio
async def test_submit_and_aggregate_round(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "test-fed", MODEL_ID)
    fid = fed["federation_id"]
    await coordinator.join_federation(db, fid, "p1")
    await coordinator.join_federation(db, fid, "p2")
    rnd = await coordinator.start_round(db, fid)
    rid = rnd["round_id"]

    update1 = _serialize_update({"dense": np.array([1.0, 2.0, 3.0])})
    update2 = _serialize_update({"dense": np.array([3.0, 4.0, 5.0])})

    r1 = await coordinator.submit_update(db, fid, rid, "p1", update1, {"loss": 0.5, "sample_count": 100})
    assert r1["received"] is True
    assert r1["updates_so_far"] == 1

    r2 = await coordinator.submit_update(db, fid, rid, "p2", update2, {"loss": 0.3, "sample_count": 100})
    assert r2["received"] is True
    assert r2["updates_so_far"] == 2

    agg = await coordinator.aggregate_round(db, fid, rid)
    assert agg["round_complete"] is True
    assert agg["participants"] == 2
    assert "loss" in agg["avg_metrics"]


# ---------------------------------------------------------------------------
# Aggregation methods
# ---------------------------------------------------------------------------


@pytest.fixture
def aggregator():
    return FederatedAggregator()


def test_fedavg_aggregation(aggregator):
    updates = [
        {"dense": np.array([1.0, 2.0])},
        {"dense": np.array([3.0, 4.0])},
    ]
    weights = [1.0, 1.0]
    result = aggregator.fedavg(updates, weights)
    np.testing.assert_array_almost_equal(result["dense"], [2.0, 3.0])


def test_fedavg_weighted(aggregator):
    updates = [
        {"dense": np.array([1.0, 0.0])},
        {"dense": np.array([3.0, 4.0])},
    ]
    weights = [3.0, 1.0]
    result = aggregator.fedavg(updates, weights)
    # (3*[1,0] + 1*[3,4])/4 = [6/4, 4/4] = [1.5, 1.0]
    np.testing.assert_array_almost_equal(result["dense"], [1.5, 1.0])


def test_trimmed_mean_robust(aggregator):
    # One outlier should be trimmed
    updates = [
        {"dense": np.array([1.0])},
        {"dense": np.array([1.0])},
        {"dense": np.array([1.0])},
        {"dense": np.array([1.0])},
        {"dense": np.array([100.0])},  # outlier
    ]
    weights = [1.0] * 5
    result = aggregator.trimmed_mean(updates, weights, trim_ratio=0.2)
    # After trimming 1 from top and bottom: [1.0, 1.0, 1.0] -> mean = 1.0
    assert result["dense"][0] == pytest.approx(1.0, abs=0.01)


def test_validate_update_catches_nan(aggregator):
    global_model = {"dense": np.array([1.0, 2.0])}
    bad_update = {"dense": np.array([float("nan"), 2.0])}
    result = aggregator.validate_update(bad_update, global_model)
    assert result["valid"] is False
    assert any("NaN" in issue for issue in result["issues"])


def test_validate_update_catches_inf(aggregator):
    global_model = {"dense": np.array([1.0, 2.0])}
    bad_update = {"dense": np.array([float("inf"), 2.0])}
    result = aggregator.validate_update(bad_update, global_model)
    assert result["valid"] is False
    assert any("Inf" in issue for issue in result["issues"])


def test_validate_update_catches_shape_mismatch(aggregator):
    global_model = {"dense": np.array([1.0, 2.0])}
    bad_update = {"dense": np.array([1.0, 2.0, 3.0])}
    result = aggregator.validate_update(bad_update, global_model)
    assert result["valid"] is False
    assert any("shape" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# Differential privacy
# ---------------------------------------------------------------------------


@pytest.fixture
def dp():
    return DifferentialPrivacy()


def test_differential_privacy_adds_noise(dp):
    gradients = {"dense": np.zeros(100)}
    noised = dp.add_noise(gradients, epsilon=1.0)
    # Noise should make the result non-zero
    assert not np.allclose(noised["dense"], 0.0)


def test_gradient_clipping(dp):
    gradients = {"dense": np.array([100.0, 200.0, 300.0])}
    clipped = dp.clip_gradients(gradients, max_norm=1.0)
    total_norm = np.linalg.norm(clipped["dense"])
    assert total_norm <= 1.0 + 1e-6


def test_privacy_budget_tracking(dp):
    budget = dp.compute_privacy_budget(rounds=10, epsilon_per_round=0.1)
    assert budget["total_epsilon"] > 0
    assert budget["total_delta"] > 0
    assert "privacy_guarantee" in budget


def test_budget_exhaustion(dp):
    assert dp.is_budget_exhausted(1.0, 1.0) is True
    assert dp.is_budget_exhausted(1.1, 1.0) is True
    assert dp.is_budget_exhausted(0.5, 1.0) is False


def test_privacy_report(dp):
    report = dp.privacy_report(
        federation_id="fed-123",
        epsilon_spent=0.2,
        epsilon_budget=1.0,
        rounds_completed=10,
        max_rounds=50,
    )
    assert report["privacy_level"] == "strong"
    assert report["rounds_remaining"] > 0
    assert report["epsilon_spent"] == 0.2


# ---------------------------------------------------------------------------
# Secure aggregation stub
# ---------------------------------------------------------------------------


def test_secure_aggregation_encrypt_decrypt():
    sa = SecureAggregation()
    update = {"dense": np.array([1.0, 2.0, 3.0])}
    encrypted = sa.encrypt_update_stub(update)
    assert "encrypted" in encrypted
    assert "note" in encrypted

    result = sa.aggregate_encrypted_stub([encrypted, encrypted])
    np.testing.assert_array_almost_equal(result["result"]["dense"], [1.0, 2.0, 3.0])
    assert result["method"] == "simulated_secure_sum"


# ---------------------------------------------------------------------------
# API route smoke tests (using coordinator directly, no HTTP server needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create(coordinator, db):
    result = await coordinator.create_federation(
        db, WORKSPACE_ID, "api-test", MODEL_ID, {"min_participants": 3}
    )
    assert result["config"]["min_participants"] == 3


@pytest.mark.asyncio
async def test_api_join(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "api-test", MODEL_ID)
    r = await coordinator.join_federation(db, fed["federation_id"], "node-1")
    assert r["joined"] is True


@pytest.mark.asyncio
async def test_api_status(coordinator, db):
    fed = await coordinator.create_federation(db, WORKSPACE_ID, "api-test", MODEL_ID)
    fid = fed["federation_id"]
    await coordinator.join_federation(db, fid, "node-1")
    status = await coordinator.get_federation_status(db, fid)
    assert status["status"] == "created"
    assert len(status["participants"]) == 1
