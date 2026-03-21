"""API routes for the Evaluation Lab — benchmarks, tournament, threshold analysis, scorecards."""

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


class ThresholdCurvesRequest(BaseModel):
    predictions: list[float]
    ground_truth: list[int]


class PRPointOut(BaseModel):
    recall: float
    precision: float
    threshold: float


class ROCPointOut(BaseModel):
    fpr: float
    tpr: float
    threshold: float


class ThresholdStatOut(BaseModel):
    threshold: float
    precision: float
    recall: float
    f1: float
    fpr: float
    accuracy: float


class ThresholdCurvesOut(BaseModel):
    pr_curve: list[PRPointOut]
    roc_curve: list[ROCPointOut]
    auc_pr: float
    auc_roc: float
    threshold_stats: list[ThresholdStatOut]
    optimal_f1_threshold: float
    optimal_precision_threshold: float
    optimal_recall_threshold: float


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


@router.post("/threshold-curves", response_model=ThresholdCurvesOut)
async def threshold_curves(body: ThresholdCurvesRequest) -> ThresholdCurvesOut:
    """Compute PR and ROC curves with AUC values and optimal thresholds.

    Returns fine-grained curve data (101 threshold steps from 0 to 1)
    suitable for rendering interactive PR and ROC charts.
    """
    if len(body.predictions) != len(body.ground_truth):
        raise HTTPException(
            status_code=400,
            detail="predictions and ground_truth must have the same length",
        )

    n = len(body.predictions)

    # Generate 101 thresholds from 0.00 to 1.00
    thresholds = [round(i * 0.01, 2) for i in range(101)]

    pr_curve: list[PRPointOut] = []
    roc_curve: list[ROCPointOut] = []
    threshold_stats: list[ThresholdStatOut] = []

    best_f1 = -1.0
    best_f1_threshold = 0.5
    best_precision = -1.0
    best_precision_threshold = 0.5
    best_recall = -1.0
    best_recall_threshold = 0.5

    for t in thresholds:
        tp = fp = tn = fn = 0
        for pred, truth in zip(body.predictions, body.ground_truth):
            predicted = 1 if pred >= t else 0
            if predicted == 1 and truth == 1:
                tp += 1
            elif predicted == 1 and truth == 0:
                fp += 1
            elif predicted == 0 and truth == 0:
                tn += 1
            else:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = recall
        accuracy = (tp + tn) / n if n > 0 else 0.0

        pr_curve.append(PRPointOut(recall=round(recall, 4), precision=round(precision, 4), threshold=t))
        roc_curve.append(ROCPointOut(fpr=round(fpr, 4), tpr=round(tpr, 4), threshold=t))
        threshold_stats.append(
            ThresholdStatOut(
                threshold=t,
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1=round(f1, 4),
                fpr=round(fpr, 4),
                accuracy=round(accuracy, 4),
            )
        )

        if f1 > best_f1:
            best_f1 = f1
            best_f1_threshold = t

        # Best precision with recall > 0
        if recall > 0 and precision > best_precision:
            best_precision = precision
            best_precision_threshold = t

        # Best recall with precision > 0
        if precision > 0 and recall > best_recall:
            best_recall = recall
            best_recall_threshold = t

    # Sort PR curve by recall ascending for proper curve rendering
    pr_curve_sorted = sorted(pr_curve, key=lambda p: (p.recall, -p.precision))

    # Sort ROC curve by FPR ascending for proper curve rendering
    roc_curve_sorted = sorted(roc_curve, key=lambda p: (p.fpr, p.tpr))

    # Compute AUC using trapezoidal rule
    auc_pr = 0.0
    for i in range(1, len(pr_curve_sorted)):
        dx = pr_curve_sorted[i].recall - pr_curve_sorted[i - 1].recall
        avg_y = (pr_curve_sorted[i].precision + pr_curve_sorted[i - 1].precision) / 2
        auc_pr += dx * avg_y
    auc_pr = round(max(0.0, min(1.0, auc_pr)), 4)

    auc_roc = 0.0
    for i in range(1, len(roc_curve_sorted)):
        dx = roc_curve_sorted[i].fpr - roc_curve_sorted[i - 1].fpr
        avg_y = (roc_curve_sorted[i].tpr + roc_curve_sorted[i - 1].tpr) / 2
        auc_roc += dx * avg_y
    auc_roc = round(max(0.0, min(1.0, auc_roc)), 4)

    return ThresholdCurvesOut(
        pr_curve=pr_curve_sorted,
        roc_curve=roc_curve_sorted,
        auc_pr=auc_pr,
        auc_roc=auc_roc,
        threshold_stats=threshold_stats,
        optimal_f1_threshold=best_f1_threshold,
        optimal_precision_threshold=best_precision_threshold,
        optimal_recall_threshold=best_recall_threshold,
    )


@router.get("/scorecard/{model_id}", response_model=ScorecardOut)
async def get_scorecard(
    model_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScorecardOut:
    """Generate a scorecard for a specific model."""
    result = await EvaluationService.generate_scorecard(db, model_id)
    return ScorecardOut(**result)
