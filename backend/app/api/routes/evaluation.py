"""API routes for the Evaluation Lab — benchmarks, tournament, threshold analysis, scorecards."""

import math
import random
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
# Bracket-style single-elimination tournament schemas
# ---------------------------------------------------------------------------


class BracketMatchup(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_a: str
    model_b: str
    winner: str
    score_a: float
    score_b: float


class BracketRound(BaseModel):
    round: int
    label: str
    matchups: list[BracketMatchup]


class BracketTournamentRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    title: str = "Untitled Tournament"
    model_ids: list[str]
    dataset_id: str
    metric: str = "accuracy"


class BracketTournamentOut(BaseModel):
    id: str
    title: str
    metric: str
    rounds: list[BracketRound]
    winner: str
    created_at: str


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


@router.post("/tournament/bracket", response_model=BracketTournamentOut)
async def run_bracket_tournament(
    body: BracketTournamentRequest,
) -> BracketTournamentOut:
    """Run a single-elimination bracket tournament (mock/stub).

    Accepts 4, 8, or 16 models. Pads to the next power-of-two if needed.
    Returns round-by-round matchups with scores and an overall winner.
    """
    if len(body.model_ids) < 4:
        raise HTTPException(
            status_code=400,
            detail="At least 4 models are required for a bracket tournament",
        )

    # Pad to next power of two with BYE entries
    n = len(body.model_ids)
    bracket_size = 2 ** math.ceil(math.log2(n))
    participants = list(body.model_ids)
    while len(participants) < bracket_size:
        participants.append(f"BYE-{len(participants)}")

    # Shuffle for seeding
    random.shuffle(participants)

    # Generate per-model base score for the chosen metric
    model_strength: dict[str, float] = {
        mid: random.uniform(0.60, 0.96) for mid in participants
    }
    # BYE models always lose
    for mid in participants:
        if mid.startswith("BYE-"):
            model_strength[mid] = 0.0

    rounds: list[BracketRound] = []
    current_participants = list(participants)
    total_rounds = int(math.log2(bracket_size))

    round_labels = {
        1: "Finals",
        2: "Semifinals",
        3: "Quarterfinals",
    }

    for r_idx in range(total_rounds):
        round_num = r_idx + 1
        rounds_remaining = total_rounds - r_idx
        label = round_labels.get(rounds_remaining, f"Round {round_num}")

        matchups: list[BracketMatchup] = []
        next_round: list[str] = []

        for i in range(0, len(current_participants), 2):
            ma = current_participants[i]
            mb = current_participants[i + 1]

            # Simulate scores with some noise
            sa = round(
                min(1.0, max(0.0, model_strength[ma] + random.uniform(-0.05, 0.05))),
                4,
            )
            sb = round(
                min(1.0, max(0.0, model_strength[mb] + random.uniform(-0.05, 0.05))),
                4,
            )

            winner = ma if sa >= sb else mb
            matchups.append(
                BracketMatchup(
                    model_a=ma,
                    model_b=mb,
                    winner=winner,
                    score_a=sa,
                    score_b=sb,
                )
            )
            next_round.append(winner)

        rounds.append(BracketRound(round=round_num, label=label, matchups=matchups))
        current_participants = next_round

    overall_winner = current_participants[0]

    return BracketTournamentOut(
        id=str(uuid.uuid4()),
        title=body.title,
        metric=body.metric,
        rounds=rounds,
        winner=overall_winner,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


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
