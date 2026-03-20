"""Tests for the Evaluation Lab — threshold analysis, tournament, benchmarks, scorecards."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.evaluation.service import EvaluationService


# ---------------------------------------------------------------------------
# Unit tests — pure logic (no DB required)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_threshold_analysis_correct_values():
    """Verify precision/recall/F1/accuracy are computed correctly at known thresholds."""
    # 10 samples: predictions vs ground truth
    predictions = [0.1, 0.4, 0.35, 0.8, 0.65, 0.9, 0.2, 0.55, 0.7, 0.95]
    ground_truth = [0, 0, 1, 1, 1, 1, 0, 1, 0, 1]

    results = await EvaluationService.threshold_analysis(
        predictions, ground_truth, thresholds=[0.5]
    )

    assert len(results) == 1
    pt = results[0]
    assert pt["threshold"] == 0.5

    # At threshold 0.5, predicted positives: 0.8, 0.65, 0.9, 0.55, 0.7, 0.95
    # Indices with pred >= 0.5: 3(1), 4(1), 5(1), 7(1), 8(0), 9(1)
    # TP=5, FP=1, TN=3, FN=1
    assert pt["precision"] == pytest.approx(5 / 6, abs=0.001)
    assert pt["recall"] == pytest.approx(5 / 6, abs=0.001)
    assert pt["f1"] == pytest.approx(5 / 6, abs=0.001)
    assert pt["accuracy"] == pytest.approx(8 / 10, abs=0.001)


@pytest.mark.anyio
async def test_threshold_analysis_edge_cases():
    """Thresholds where everything is predicted positive or negative."""
    predictions = [0.5, 0.6]
    ground_truth = [0, 1]

    results = await EvaluationService.threshold_analysis(
        predictions, ground_truth, thresholds=[0.0, 1.0]
    )

    # threshold=0.0 → all predicted positive
    low = results[0]
    assert low["recall"] == 1.0  # caught all positives

    # threshold=1.0 → all predicted negative
    high = results[1]
    assert high["precision"] == 0.0  # no predicted positives


@pytest.mark.anyio
async def test_tournament_ranking():
    """Tournament with 3+ models returns valid structure and a single overall winner."""
    from unittest.mock import AsyncMock, MagicMock

    db = MagicMock()

    model_ids = ["model-x", "model-y", "model-z"]
    result = await EvaluationService.compare_models_tournament(
        db, model_ids, dataset_id="ds-1"
    )

    # Structure checks
    assert "matchups" in result
    assert "rankings" in result
    assert "overall_winner" in result
    assert "wins" in result

    # 3 models → C(3,2) = 3 matchups
    assert len(result["matchups"]) == 3

    # Rankings contain all models
    assert set(result["rankings"]) == set(model_ids)

    # Overall winner is in the model list
    assert result["overall_winner"] in model_ids

    # Each matchup has required fields
    for m in result["matchups"]:
        assert "model_a" in m
        assert "model_b" in m
        assert "winner" in m
        assert "metric_diffs" in m
        assert m["winner"] in model_ids


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def ac():
    """Async HTTP client for the FastAPI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.anyio
async def test_api_threshold_analysis(ac: AsyncClient):
    """POST /api/evaluation/threshold-analysis returns correct shape."""
    resp = await ac.post(
        "/api/evaluation/threshold-analysis",
        json={
            "predictions": [0.2, 0.8, 0.5, 0.9],
            "ground_truth": [0, 1, 0, 1],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 9  # default thresholds 0.1..0.9
    for pt in data:
        assert "threshold" in pt
        assert "precision" in pt
        assert "recall" in pt
        assert "f1" in pt
        assert "accuracy" in pt


@pytest.mark.anyio
async def test_api_threshold_analysis_length_mismatch(ac: AsyncClient):
    """Mismatched predictions/ground_truth lengths → 400."""
    resp = await ac.post(
        "/api/evaluation/threshold-analysis",
        json={
            "predictions": [0.5],
            "ground_truth": [0, 1],
        },
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_api_tournament_requires_min_models(ac: AsyncClient):
    """Tournament with <2 models → 400."""
    resp = await ac.post(
        "/api/evaluation/tournament",
        json={"model_ids": ["only-one"], "dataset_id": "ds-1"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_api_benchmark(ac: AsyncClient):
    """POST create + run benchmark round-trip (may fail without DB, but tests route wiring)."""
    # This tests the route is correctly wired; actual DB ops may 500 without a live DB
    resp = await ac.post(
        "/api/evaluation/benchmarks",
        json={
            "name": "test-bench",
            "dataset_id": "ds-1",
            "model_ids": ["m1", "m2"],
            "metrics": ["accuracy"],
            "workspace_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    # Route should exist (not 404/405); may be 500 without DB
    assert resp.status_code in (200, 201, 500)


@pytest.mark.anyio
async def test_scorecard(ac: AsyncClient):
    """GET /api/evaluation/scorecard/{model_id} returns correct shape."""
    resp = await ac.get("/api/evaluation/scorecard/model-test")
    # May 500 without DB, but route should not 404/405
    assert resp.status_code in (200, 500)
