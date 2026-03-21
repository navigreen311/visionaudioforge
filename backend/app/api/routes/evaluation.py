"""API routes for the Evaluation Lab — benchmarks, tournament, threshold analysis, scorecards."""

import random
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.evaluation.service import EvaluationService

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class BenchmarkCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: str
    dataset_id: str
    model_ids: list[str]
    metrics: list[str] = Field(default_factory=lambda: ["accuracy", "precision", "recall", "f1"])
    workspace_id: str


class BenchmarkOut(BaseModel):
    id: str
    type: str
    payload: dict[str, Any]

    class Config:
        from_attributes = True


class BenchmarkRunOut(BaseModel):
    results: dict[str, dict[str, float]]
    ranking: list[str]
    duration_ms: float


class TournamentRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_ids: list[str]
    dataset_id: str


class TournamentOut(BaseModel):
    matchups: list[dict[str, Any]]
    rankings: list[str]
    overall_winner: str
    wins: dict[str, int]


class ThresholdRequest(BaseModel):
    predictions: list[float]
    ground_truth: list[int]
    thresholds: list[float] | None = None


class ThresholdPoint(BaseModel):
    threshold: float
    precision: float
    recall: float
    f1: float
    accuracy: float


class ScorecardOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    model: str
    benchmarks: list[dict[str, Any]]
    avg_scores: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/benchmarks", response_model=BenchmarkOut)
async def create_benchmark(
    body: BenchmarkCreate,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkOut:
    """Create a new benchmark configuration."""
    event = await EvaluationService.create_benchmark(
        db,
        name=body.name,
        dataset_id=body.dataset_id,
        model_ids=body.model_ids,
        metrics=body.metrics,
        workspace_id=body.workspace_id,
    )
    return BenchmarkOut(id=str(event.id), type=event.type, payload=event.payload)


@router.post("/benchmarks/{benchmark_id}/run", response_model=BenchmarkRunOut)
async def run_benchmark(
    benchmark_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunOut:
    """Run a previously created benchmark and return results."""
    try:
        result = await EvaluationService.run_benchmark(db, str(benchmark_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return BenchmarkRunOut(**result)


@router.post("/tournament", response_model=TournamentOut)
async def run_tournament(
    body: TournamentRequest,
    db: AsyncSession = Depends(get_db),
) -> TournamentOut:
    """Run a round-robin tournament comparing models."""
    if len(body.model_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models required for a tournament")
    result = await EvaluationService.compare_models_tournament(db, body.model_ids, body.dataset_id)
    return TournamentOut(**result)


@router.post("/threshold-analysis", response_model=list[ThresholdPoint])
async def threshold_analysis(body: ThresholdRequest) -> list[ThresholdPoint]:
    """Compute precision/recall/F1/accuracy across decision thresholds."""
    if len(body.predictions) != len(body.ground_truth):
        raise HTTPException(
            status_code=400,
            detail="predictions and ground_truth must have the same length",
        )
    results = await EvaluationService.threshold_analysis(
        body.predictions, body.ground_truth, body.thresholds
    )
    return [ThresholdPoint(**r) for r in results]


class BenchmarkRunRequest(BaseModel):
    """Standalone benchmark run — create + execute in one call."""

    model_config = {"protected_namespaces": ()}
    name: str
    dataset_id: str
    model_ids: list[str] = Field(..., min_length=2, max_length=10)
    metrics: list[str] = Field(default_factory=lambda: ["accuracy", "precision", "recall", "f1"])
    workspace_id: str | None = None


@router.post("/benchmark", response_model=BenchmarkRunOut)
async def run_benchmark_standalone(body: BenchmarkRunRequest) -> BenchmarkRunOut:
    """Create and run a benchmark in a single call, returning mock results."""
    start = time.monotonic()

    # Generate deterministic-ish mock scores per model per metric
    results: dict[str, dict[str, float]] = {}
    for model_id in body.model_ids:
        seed = hash(model_id + body.dataset_id) & 0xFFFFFFFF
        rng = random.Random(seed)
        scores: dict[str, float] = {}
        for metric in body.metrics:
            scores[metric] = round(rng.uniform(0.55, 0.98), 4)
        results[model_id] = scores

    # Rank by average score descending
    def avg_score(mid: str) -> float:
        vals = results[mid].values()
        return sum(vals) / len(vals) if vals else 0.0

    ranking = sorted(body.model_ids, key=avg_score, reverse=True)
    duration_ms = round((time.monotonic() - start) * 1000, 2)

    return BenchmarkRunOut(results=results, ranking=ranking, duration_ms=duration_ms)


@router.get("/scorecard/{model_id}", response_model=ScorecardOut)
async def get_scorecard(
    model_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScorecardOut:
    """Generate a scorecard for a specific model."""
    result = await EvaluationService.generate_scorecard(db, model_id)
    return ScorecardOut(**result)
