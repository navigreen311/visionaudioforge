"""Tests for Validation & Trust module (M12) — calibration, drift, uncertainty,
model cards, audit trails, explainability, and API endpoints."""

from __future__ import annotations

import io
import math
import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.core.deps import get_db
from app.main import app
from app.services.validation.service import ValidationService
from app.services.validation.explainability import ExplainabilityService

svc = ValidationService()
explain_svc = ExplainabilityService()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_ece_calculation():
    """ECE should reflect the gap between confidence and accuracy."""
    # Perfectly calibrated: confidence matches accuracy
    predictions = [0.1] * 5 + [0.9] * 5
    ground_truth = [0, 0, 0, 0, 1] + [1, 1, 1, 1, 0]
    # bin 0.0-0.1: avg_conf=0.1, acc=1/5=0.2 -> gap 0.1
    # bin 0.8-0.9: avg_conf=0.9, acc=4/5=0.8 -> gap 0.1
    result = await svc.calibration_analysis(predictions, ground_truth, n_bins=10)

    assert "ece" in result
    assert "mce" in result
    assert "bins" in result
    assert isinstance(result["ece"], float)
    assert result["ece"] >= 0
    assert result["mce"] >= result["ece"] or result["mce"] == result["ece"]
    assert len(result["bins"]) == 10

    # Well-calibrated model should have low ECE
    perfect_preds = [0.9] * 10
    perfect_gt = [1] * 10
    perfect_result = await svc.calibration_analysis(perfect_preds, perfect_gt, n_bins=10)
    assert perfect_result["ece"] < 0.15  # low miscalibration


@pytest.mark.anyio
async def test_calibration_perfectly_calibrated():
    """A perfectly calibrated model should have ECE = 0."""
    # All predictions in one bin with 100% accuracy
    predictions = [0.95] * 10
    ground_truth = [1] * 10
    result = await svc.calibration_analysis(predictions, ground_truth, n_bins=10)
    # avg_conf = 0.95, accuracy = 1.0, gap = 0.05
    assert result["ece"] == pytest.approx(0.05, abs=0.01)


# ---------------------------------------------------------------------------
# Drift Detection
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_drift_detection_triggers():
    """Drift should be detected when current mean diverges > 2*ref_std."""
    reference = {
        "feature_a": {"mean": 0.5, "std": 0.1},
        "feature_b": {"mean": 10.0, "std": 1.0},
    }
    current = {
        "feature_a": {"mean": 0.5, "std": 0.1},  # no drift
        "feature_b": {"mean": 15.0, "std": 1.0},  # drift: |15-10| = 5 > 2*1
    }
    result = await svc.drift_detection(reference, current)

    assert result["drift_detected"] is True
    assert "feature_b" in result["drifted_features"]
    assert "feature_a" not in result["drifted_features"]
    assert result["drift_score"] > 2.0


@pytest.mark.anyio
async def test_drift_no_drift():
    """No drift when distributions are similar."""
    reference = {
        "feature_a": {"mean": 0.5, "std": 0.1},
        "feature_b": {"mean": 10.0, "std": 1.0},
    }
    current = {
        "feature_a": {"mean": 0.52, "std": 0.1},  # within 2*0.1
        "feature_b": {"mean": 10.5, "std": 1.0},  # within 2*1.0
    }
    result = await svc.drift_detection(reference, current)

    assert result["drift_detected"] is False
    assert result["drifted_features"] == []
    assert "No significant drift" in result["recommendation"]


# ---------------------------------------------------------------------------
# Uncertainty Estimation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_uncertainty_entropy():
    """Entropy should be high for uniform distributions and low for confident ones."""
    # Uniform distribution (maximum uncertainty for 3 classes)
    uniform = [[1 / 3, 1 / 3, 1 / 3]]
    result_uniform = await svc.uncertainty_estimation(uniform)
    assert result_uniform["per_sample"][0]["is_uncertain"] is True
    assert result_uniform["per_sample"][0]["entropy"] > 0.5

    # Confident prediction (low uncertainty)
    confident = [[0.95, 0.03, 0.02]]
    result_confident = await svc.uncertainty_estimation(confident)
    assert result_confident["per_sample"][0]["is_uncertain"] is False
    assert result_confident["per_sample"][0]["entropy"] < 0.5

    # Entropy of uniform should be higher than confident
    assert (
        result_uniform["per_sample"][0]["entropy"]
        > result_confident["per_sample"][0]["entropy"]
    )


# ---------------------------------------------------------------------------
# Model Card (unit test with mock DB)
# ---------------------------------------------------------------------------

def _mock_model_record(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "name": "resnet50-detector",
        "version": "2.1.0",
        "status": "production",
        "backbone": "ResNet50",
        "metrics": {"accuracy": 0.94, "f1": 0.91},
        "workspace_id": uuid.uuid4(),
        "created_at": "2026-03-20T00:00:00Z",
        "updated_at": "2026-03-20T00:00:00Z",
    }
    defaults.update(overrides)
    record = MagicMock()
    for k, v in defaults.items():
        setattr(record, k, v)
    return record


@pytest.mark.anyio
async def test_model_card():
    """Model card should contain all required sections."""
    record = _mock_model_record()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    db.execute = AsyncMock(return_value=mock_result)

    card = await svc.generate_model_card(db, record.id)

    assert card["model_name"] == "resnet50-detector"
    assert card["version"] == "2.1.0"
    assert "description" in card
    assert "metrics" in card
    assert "intended_use" in card
    assert "limitations" in card
    assert "training_data" in card
    assert "evaluation_results" in card
    assert "ethical_considerations" in card


# ---------------------------------------------------------------------------
# API-level test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_calibration(test_app):
    """POST /api/validate/calibration should return bins and ECE."""
    payload = {
        "predictions": [0.1, 0.2, 0.3, 0.7, 0.8, 0.9],
        "ground_truth": [0, 0, 0, 1, 1, 1],
        "n_bins": 10,
    }
    resp = await test_app.post("/api/validate/calibration", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "ece" in data
    assert "mce" in data
    assert "bins" in data
    assert "is_calibrated" in data
    assert len(data["bins"]) == 10


@pytest.mark.anyio
async def test_api_drift(test_app):
    """POST /api/validate/drift should return drift analysis."""
    payload = {
        "reference_stats": {"f1": {"mean": 5.0, "std": 1.0}},
        "current_stats": {"f1": {"mean": 5.5, "std": 1.0}},
    }
    resp = await test_app.post("/api/validate/drift", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "drift_detected" in data
    assert data["drift_detected"] is False


@pytest.mark.anyio
async def test_api_uncertainty(test_app):
    """POST /api/validate/uncertainty should return entropy analysis."""
    payload = {"predictions": [[0.8, 0.2], [0.5, 0.5]]}
    resp = await test_app.post("/api/validate/uncertainty", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "per_sample" in data
    assert len(data["per_sample"]) == 2
    assert "avg_entropy" in data


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_feature_attribution():
    """Feature attribution should rank features by correlation."""
    features = {
        "brightness": [0.1, 0.3, 0.5, 0.7, 0.9],
        "noise": [0.5, 0.5, 0.5, 0.5, 0.5],  # no variance -> 0 importance
    }
    predictions = [0.1, 0.3, 0.5, 0.7, 0.9]
    result = await explain_svc.feature_attribution(features, predictions)
    assert len(result) == 2
    # brightness should have high importance (perfect correlation)
    assert result[0]["feature"] == "brightness"
    assert abs(result[0]["importance"]) > 0.9
    # noise should have zero importance
    assert result[1]["importance"] == 0.0


@pytest.mark.anyio
async def test_generate_explanation():
    """Explanation should contain prediction, confidence, factors, and text."""
    result = await explain_svc.generate_explanation(
        prediction="cat",
        confidence=0.92,
        features={"fur_texture": 0.8, "ear_shape": 0.6, "tail_length": 0.3},
    )
    assert result["prediction"] == "cat"
    assert result["confidence"] == 0.92
    assert len(result["top_factors"]) == 3
    assert "cat" in result["explanation_text"]
    assert "high confidence" in result["explanation_text"]


# ---------------------------------------------------------------------------
# API: Model Card endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_model_card(test_app):
    """GET /api/validate/model-card/{id} should return a full model card."""
    record = _mock_model_record()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    mock_db.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        resp = await test_app.get(f"/api/validate/model-card/{record.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "resnet50-detector"
        assert data["version"] == "2.1.0"
        assert "description" in data
        assert "metrics" in data
        assert "intended_use" in data
        assert "limitations" in data
        assert "training_data" in data
        assert "evaluation_results" in data
        assert "ethical_considerations" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_model_card_not_found(test_app):
    """GET /api/validate/model-card/{id} should return 404 for unknown model."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    missing_id = uuid.uuid4()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        resp = await test_app.get(f"/api/validate/model-card/{missing_id}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# API: Audit Trail endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_audit_trail(test_app):
    """GET /api/validate/audit/{id} should return audit events."""
    record = _mock_model_record()
    # Make updated_at differ from created_at so we get two events
    record.updated_at = "2026-03-20T12:00:00Z"
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    mock_db.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        resp = await test_app.get(f"/api/validate/audit/{record.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == str(record.id)
        assert "events" in data
        assert len(data["events"]) >= 1
        assert data["events"][0]["event"] == "model_registered"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_audit_trail_not_found(test_app):
    """GET /api/validate/audit/{id} should return empty events for unknown model."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    missing_id = uuid.uuid4()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        resp = await test_app.get(f"/api/validate/audit/{missing_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# API: Explain endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_explain(test_app):
    """POST /api/validate/explain should return a saliency map."""
    # Create a small 4x4 grayscale image (16 bytes = 4*4)
    img_bytes = np.random.randint(0, 255, (16,), dtype=np.uint8).tobytes()
    resp = await test_app.post(
        "/api/validate/explain",
        files={"file": ("test.raw", io.BytesIO(img_bytes), "application/octet-stream")},
        data={"model_output": "{}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "saliency_map_base64" in data
    assert "shape" in data
    assert len(data["shape"]) == 2
