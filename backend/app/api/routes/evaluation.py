"""API routes for the Evaluation Lab — benchmarks, tournament, threshold analysis, scorecards."""

import math
import uuid
from datetime import datetime, timezone
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


@router.get("/scorecard/{model_id}", response_model=ScorecardOut)
async def get_scorecard(
    model_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScorecardOut:
    """Generate a scorecard for a specific model."""
    result = await EvaluationService.generate_scorecard(db, model_id)
    return ScorecardOut(**result)


# ---------------------------------------------------------------------------
# Stub / mock endpoints (return realistic data without DB)
# ---------------------------------------------------------------------------


class BenchmarkResultModel(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str
    model_name: str
    metrics: dict[str, float]


class BenchmarkResultOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    name: str
    dataset_id: str
    models: list[BenchmarkResultModel]
    best_model_id: str
    created_at: str
    duration_ms: float


class BenchmarkSummary(BaseModel):
    id: str
    name: str
    dataset_id: str
    model_count: int
    best_model_id: str
    best_score: float
    status: str
    created_at: str


class TournamentMatch(BaseModel):
    model_config = {"protected_namespaces": ()}
    round: int
    model_a: str
    model_b: str
    winner: str
    score_a: float
    score_b: float


class TournamentBracketOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    rounds: list[list[TournamentMatch]]
    overall_winner: str
    model_rankings: list[dict[str, Any]]


class CurvePoint(BaseModel):
    x: float
    y: float


class ThresholdTableRow(BaseModel):
    threshold: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    tn: int
    accuracy: float


class ThresholdAnalysisOut(BaseModel):
    pr_curve: list[CurvePoint]
    roc_curve: list[CurvePoint]
    optimal_f1_threshold: float
    threshold_table: list[ThresholdTableRow]


@router.post("/benchmark", response_model=BenchmarkResultOut)
async def run_benchmark_stub() -> BenchmarkResultOut:
    """Run a benchmark and return mock results with 3 models, 4 metrics each."""
    models = [
        BenchmarkResultModel(
            model_id="model-resnet50-v2",
            model_name="ResNet-50 v2",
            metrics={"accuracy": 0.934, "precision": 0.921, "recall": 0.947, "f1": 0.934},
        ),
        BenchmarkResultModel(
            model_id="model-efficientnet-b4",
            model_name="EfficientNet-B4",
            metrics={"accuracy": 0.951, "precision": 0.943, "recall": 0.958, "f1": 0.950},
        ),
        BenchmarkResultModel(
            model_id="model-vit-base",
            model_name="ViT-Base/16",
            metrics={"accuracy": 0.962, "precision": 0.955, "recall": 0.968, "f1": 0.961},
        ),
    ]
    return BenchmarkResultOut(
        id="bench-" + uuid.uuid4().hex[:12],
        name="Image Classification Benchmark",
        dataset_id="ds-imagenet-val-5k",
        models=models,
        best_model_id="model-vit-base",
        created_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=4523.7,
    )


@router.get("/benchmarks", response_model=list[BenchmarkSummary])
async def list_benchmarks_stub() -> list[BenchmarkSummary]:
    """Return an array of 3 past benchmark summaries (mock data)."""
    return [
        BenchmarkSummary(
            id="bench-a1b2c3d4e5f6",
            name="Image Classification Benchmark",
            dataset_id="ds-imagenet-val-5k",
            model_count=3,
            best_model_id="model-vit-base",
            best_score=0.962,
            status="completed",
            created_at="2026-03-18T14:30:00Z",
        ),
        BenchmarkSummary(
            id="bench-f6e5d4c3b2a1",
            name="Object Detection Benchmark",
            dataset_id="ds-coco-val-2k",
            model_count=4,
            best_model_id="model-yolov8-xl",
            best_score=0.891,
            status="completed",
            created_at="2026-03-15T09:15:00Z",
        ),
        BenchmarkSummary(
            id="bench-112233445566",
            name="Audio Event Classification",
            dataset_id="ds-audioset-eval-1k",
            model_count=2,
            best_model_id="model-ast-base",
            best_score=0.877,
            status="completed",
            created_at="2026-03-10T16:45:00Z",
        ),
    ]


@router.post("/tournament/bracket", response_model=TournamentBracketOut)
async def run_tournament_bracket_stub() -> TournamentBracketOut:
    """Run a tournament and return mock bracket with 2 rounds."""
    round1 = [
        TournamentMatch(
            round=1,
            model_a="model-resnet50-v2",
            model_b="model-efficientnet-b4",
            winner="model-efficientnet-b4",
            score_a=0.934,
            score_b=0.951,
        ),
        TournamentMatch(
            round=1,
            model_a="model-vit-base",
            model_b="model-convnext-t",
            winner="model-vit-base",
            score_a=0.962,
            score_b=0.945,
        ),
    ]
    round2 = [
        TournamentMatch(
            round=2,
            model_a="model-efficientnet-b4",
            model_b="model-vit-base",
            winner="model-vit-base",
            score_a=0.951,
            score_b=0.962,
        ),
    ]
    return TournamentBracketOut(
        id="tourn-" + uuid.uuid4().hex[:12],
        rounds=[round1, round2],
        overall_winner="model-vit-base",
        model_rankings=[
            {"model_id": "model-vit-base", "rank": 1, "wins": 2, "avg_score": 0.962},
            {"model_id": "model-efficientnet-b4", "rank": 2, "wins": 1, "avg_score": 0.951},
            {"model_id": "model-resnet50-v2", "rank": 3, "wins": 0, "avg_score": 0.934},
            {"model_id": "model-convnext-t", "rank": 4, "wins": 0, "avg_score": 0.945},
        ],
    )


@router.post("/threshold-analysis/full", response_model=ThresholdAnalysisOut)
async def threshold_analysis_full_stub() -> ThresholdAnalysisOut:
    """Return mock PR curve (20 pts), ROC curve (20 pts), optimal threshold, and table (9 rows)."""
    # PR curve: precision vs recall (20 points, decreasing precision as recall increases)
    pr_curve = []
    for i in range(20):
        recall = i / 19.0
        # Simulated precision that decreases as recall increases
        precision = max(0.0, 1.0 - 0.3 * recall - 0.15 * recall * recall)
        pr_curve.append(CurvePoint(x=round(recall, 4), y=round(precision, 4)))

    # ROC curve: FPR vs TPR (20 points)
    roc_curve = []
    for i in range(20):
        fpr = i / 19.0
        # Simulated TPR that rises faster than FPR (good classifier)
        tpr = min(1.0, fpr + 0.6 * math.sqrt(fpr) + 0.2 * fpr * fpr)
        tpr = min(1.0, tpr)
        roc_curve.append(CurvePoint(x=round(fpr, 4), y=round(min(tpr, 1.0), 4)))

    # Threshold table: 9 rows from 0.1 to 0.9
    threshold_table = [
        ThresholdTableRow(threshold=0.1, precision=0.62, recall=0.98, f1=0.76, tp=490, fp=300, fn=10, tn=200, accuracy=0.69),
        ThresholdTableRow(threshold=0.2, precision=0.71, recall=0.96, f1=0.82, tp=480, fp=196, fn=20, tn=304, accuracy=0.784),
        ThresholdTableRow(threshold=0.3, precision=0.79, recall=0.93, f1=0.85, tp=465, fp=124, fn=35, tn=376, accuracy=0.841),
        ThresholdTableRow(threshold=0.4, precision=0.85, recall=0.89, f1=0.87, tp=445, fp=79, fn=55, tn=421, accuracy=0.866),
        ThresholdTableRow(threshold=0.5, precision=0.90, recall=0.84, f1=0.87, tp=420, fp=47, fn=80, tn=453, accuracy=0.873),
        ThresholdTableRow(threshold=0.6, precision=0.93, recall=0.77, f1=0.84, tp=385, fp=29, fn=115, tn=471, accuracy=0.856),
        ThresholdTableRow(threshold=0.7, precision=0.95, recall=0.68, f1=0.79, tp=340, fp=18, fn=160, tn=482, accuracy=0.822),
        ThresholdTableRow(threshold=0.8, precision=0.97, recall=0.55, f1=0.70, tp=275, fp=8, fn=225, tn=492, accuracy=0.767),
        ThresholdTableRow(threshold=0.9, precision=0.99, recall=0.38, f1=0.55, tp=190, fp=2, fn=310, tn=498, accuracy=0.688),
    ]

    return ThresholdAnalysisOut(
        pr_curve=pr_curve,
        roc_curve=roc_curve,
        optimal_f1_threshold=0.45,
        threshold_table=threshold_table,
    )
