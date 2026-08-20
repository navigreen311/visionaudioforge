"""API routes for the Evaluation Lab - benchmarks, tournament, threshold analysis, scorecards."""

import math
import uuid
from uuid import UUID
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_workspace_id
from app.models.event import Event
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
    # The ROC curve's x axis. Optional so an older caller that never sent it
    # still validates.
    fpr: float | None = None


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


class TournamentBracketRequest(BaseModel):
    """What the console's tournament tab actually posts."""

    title: str = "Untitled Tournament"
    model_ids: list[str] = Field(default_factory=list)
    dataset_id: str = ""
    metric: str = "accuracy"


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


@router.post("/threshold-curves")
async def threshold_curves(body: ThresholdRequest) -> dict:
    """PR and ROC curves with their areas, plus the three optimal thresholds.

    `ThresholdTuningTab` has posted here since it shipped and nothing answered:
    the module offers `/threshold-analysis`, which returns a flat list of
    per-threshold stats, and the tab needs curves, areas and optima. It is not a
    rename - the shapes are different - so the tab's "Analyze" button 404'd and
    reported the status code.

    Everything here is derived from the same confusion-matrix sweep that
    `/threshold-analysis` already performs, at a finer step so the curves have
    enough points to draw. Areas use the trapezoid rule over the swept points,
    which is what the curves show; no smoothing or extrapolation is applied,
    because a drawn curve and a reported area disagreeing is worse than either
    being coarse.
    """
    if len(body.predictions) != len(body.ground_truth):
        raise HTTPException(
            status_code=400,
            detail="predictions and ground_truth must have the same length",
        )
    if not body.predictions:
        raise HTTPException(status_code=400, detail="no predictions were supplied")

    thresholds = body.thresholds or [round(i / 100.0, 2) for i in range(0, 101)]
    points = await EvaluationService.threshold_analysis(
        body.predictions, body.ground_truth, thresholds
    )

    def _area(xs: list[float], ys: list[float]) -> float:
        """Trapezoid rule over points sorted by x."""
        pairs = sorted(zip(xs, ys))
        return round(
            sum(
                (pairs[i + 1][0] - pairs[i][0]) * (pairs[i + 1][1] + pairs[i][1]) / 2.0
                for i in range(len(pairs) - 1)
            ),
            6,
        )

    pr_curve = [
        {
            "threshold": p["threshold"],
            "precision": p["precision"],
            "recall": p["recall"],
        }
        for p in points
    ]
    roc_curve = [
        {"threshold": p["threshold"], "fpr": p["fpr"], "tpr": p["recall"]}
        for p in points
    ]

    def _best(key: str) -> float:
        # Ties go to the lower threshold: of two settings that score the same,
        # the more permissive one is the one an operator can reason about.
        best = max(points, key=lambda p: (p[key], -p["threshold"]))
        return best["threshold"]

    return {
        "pr_curve": pr_curve,
        "roc_curve": roc_curve,
        "auc_pr": _area([p["recall"] for p in points], [p["precision"] for p in points]),
        "auc_roc": _area([p["fpr"] for p in points], [p["recall"] for p in points]),
        "threshold_stats": points,
        "optimal_f1_threshold": _best("f1"),
        "optimal_precision_threshold": _best("precision"),
        "optimal_recall_threshold": _best("recall"),
    }


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


@router.get("/benchmarks", response_model=list[BenchmarkSummary])
async def list_benchmarks(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[BenchmarkSummary]:
    """Benchmarks this workspace has actually created.

    This returned the same three invented summaries - an ImageNet run, an audio
    run and a detection run - to every workspace, so the history panel showed
    work nobody had done and never showed work they had.
    """
    rows = (
        await db.execute(
            select(Event)
            .where(Event.workspace_id == session_workspace, Event.type == "benchmark")
            .order_by(Event.timestamp.desc())
            .limit(100)
        )
    ).scalars().all()

    summaries: list[BenchmarkSummary] = []
    for event in rows:
        payload = event.payload or {}
        results = payload.get("results") or {}
        best_model_id = None
        if isinstance(results, dict) and results:
            best_model_id = max(
                results,
                key=lambda mid: (results.get(mid) or {}).get("accuracy", 0),
            )
        summaries.append(
            BenchmarkSummary(
                id=str(event.id),
                name=payload.get("name", "benchmark"),
                dataset_id=payload.get("dataset_id", ""),
                model_count=len(payload.get("model_ids") or []),
                best_model_id=best_model_id or "",
                best_score=float(
                    ((results.get(best_model_id) or {}) if best_model_id else {}).get(
                        "accuracy", 0.0
                    )
                ),
                created_at=event.timestamp.isoformat() if event.timestamp else "",
                status=payload.get("status", "created"),
            )
        )
    return summaries


@router.post("/tournament/bracket", response_model=TournamentBracketOut)
async def run_tournament_bracket(
    body: TournamentBracketRequest,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> TournamentBracketOut:
    """Run a round-robin tournament over the selected models.

    The console posts the models the operator picked, the dataset and the
    metric. This endpoint took no body at all and returned the same two-round
    bracket between ResNet-50 and EfficientNet whatever was selected.

    The comparison itself is still simulated inside EvaluationService - there is
    no inference harness behind it - and the service flags that in its payload.
    That flag is carried through here rather than hidden, so the console can say
    so.
    """
    if len(body.model_ids) < 2:
        raise HTTPException(
            status_code=422, detail="A tournament needs at least two models."
        )

    result = await EvaluationService.compare_models_tournament(
        db, model_ids=body.model_ids, dataset_id=body.dataset_id
    )

    matches = [
        TournamentMatch(
            round=int(m.get("round", 1)),
            model_a=str(m.get("model_a", "")),
            model_b=str(m.get("model_b", "")),
            winner=str(m.get("winner", "")),
            score_a=float(m.get("score_a", 0.0)),
            score_b=float(m.get("score_b", 0.0)),
        )
        for m in result.get("matchups", [])
    ]

    rankings = [
        {"model_id": mid, "wins": wins, "simulated": bool(result.get("simulated", True))}
        for mid, wins in sorted(
            (result.get("wins") or {}).items(), key=lambda kv: -kv[1]
        )
    ]

    return TournamentBracketOut(
        id=str(uuid.uuid4()),
        rounds=[matches] if matches else [],
        overall_winner=str(result.get("winner") or (rankings[0]["model_id"] if rankings else "")),
        model_rankings=rankings,
    )


