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

# ---------------------------------------------------------------------------
# Federation lifecycle
# ---------------------------------------------------------------------------

# The lifecycle tests that lived here drove the coordinator with an AsyncMock
# session and a workspace id that was not a UUID, so they passed whether or not
# anything was written. Now that federations, participants and rounds are rows,
# they are covered against a real database in tests/test_federated_persistence.py
# — including round recording, contribution metrics, privacy-budget spend and
# restart survival. What remains in this file is the aggregation, privacy and
# secure-aggregation maths, which needs no session.


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
