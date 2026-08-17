"""Evaluation service — benchmarks, model comparison, threshold tuning, scorecards."""

import hashlib
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


def _unit_hash(*parts: str) -> float:
    """Stable pseudo-value in [0, 1) derived from *parts*.

    Deterministic across runs and processes, unlike random.*, so a benchmark
    that has not actually been executed at least reports the same placeholder
    every time instead of reshuffling the leaderboard.
    """
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def _placeholder_scores(model_id: str, metrics: list[str]) -> dict[str, float]:
    """Deterministic stand-in scores for a model that was never evaluated."""
    base = 0.65 + _unit_hash(model_id, "base") * 0.30
    scores: dict[str, float] = {}
    for metric in metrics:
        if metric == "latency_ms":
            scores[metric] = round(5.0 + _unit_hash(model_id, metric) * 195.0, 2)
        elif metric == "throughput":
            scores[metric] = round(50.0 + _unit_hash(model_id, metric) * 450.0, 2)
        else:
            spread = (_unit_hash(model_id, metric) - 0.5) * 0.16
            scores[metric] = round(min(1.0, max(0.0, base + spread)), 4)
    return scores


class EvaluationService:
    """Benchmark suite, tournament comparison, threshold analysis, and scorecards."""

    # Metrics that can be generated in simulated benchmarks
    SUPPORTED_METRICS = ["accuracy", "precision", "recall", "f1", "latency_ms", "throughput"]

    @staticmethod
    async def create_benchmark(
        db: AsyncSession,
        name: str,
        dataset_id: str,
        model_ids: list[str],
        metrics: list[str],
        workspace_id: str,
    ) -> Event:
        """Create a benchmark event that records configuration."""
        event = Event(
            id=uuid.uuid4(),
            type="benchmark",
            source="evaluation_service",
            workspace_id=uuid.UUID(workspace_id),
            payload={
                "name": name,
                "dataset_id": dataset_id,
                "model_ids": model_ids,
                "metrics": metrics,
                "status": "created",
            },
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def run_benchmark(
        db: AsyncSession,
        benchmark_id: str,
    ) -> dict[str, Any]:
        """Run a benchmark — V1 simulates realistic random metrics per model."""
        result = await db.execute(
            select(Event).where(
                Event.id == uuid.UUID(benchmark_id),
                Event.type == "benchmark",
            )
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise ValueError(f"Benchmark {benchmark_id} not found")

        payload = event.payload or {}
        model_ids: list[str] = payload.get("model_ids", [])
        metrics: list[str] = payload.get("metrics", EvaluationService.SUPPORTED_METRICS[:4])

        start = time.perf_counter()

        # No evaluation runner exists yet: nothing loads a model or scores it
        # against a dataset. Scores are therefore placeholders derived
        # deterministically from the model id, and the benchmark is marked
        # `simulated` so a ranking is never mistaken for an measured result.
        # Previously these came from random.uniform, so the "winner" changed on
        # every run and looked like a real evaluation.
        results: dict[str, dict[str, float]] = {
            model_id: _placeholder_scores(model_id, metrics) for model_id in model_ids
        }

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # Rank models by average of classification metrics (exclude latency/throughput)
        classification_metrics = [m for m in metrics if m not in ("latency_ms", "throughput")]

        def avg_score(mid: str) -> float:
            scores = [results[mid][m] for m in classification_metrics if m in results[mid]]
            return sum(scores) / len(scores) if scores else 0.0

        ranking = sorted(model_ids, key=avg_score, reverse=True)

        # Update event with results
        payload["status"] = "completed"
        payload["results"] = results
        payload["ranking"] = ranking
        payload["duration_ms"] = duration_ms
        payload["simulated"] = True
        event.payload = payload
        await db.commit()

        return {
            "results": results,
            "ranking": ranking,
            "duration_ms": duration_ms,
            # Scores are placeholders, not evaluation output. See
            # _placeholder_scores; the UI must label this run as unmeasured.
            "simulated": True,
        }

    @staticmethod
    async def compare_models_tournament(
        db: AsyncSession,
        model_ids: list[str],
        dataset_id: str,
    ) -> dict[str, Any]:
        """Round-robin tournament comparing every pair of models."""
        metrics = ["accuracy", "precision", "recall", "f1"]
        matchups: list[dict[str, Any]] = []
        wins: dict[str, int] = {mid: 0 for mid in model_ids}

        # As with run_benchmark, no model is actually scored here — the
        # round-robin logic is real but its inputs are deterministic
        # placeholders, flagged as `simulated` in the returned payload.
        model_scores: dict[str, dict[str, float]] = {
            mid: _placeholder_scores(mid, metrics) for mid in model_ids
        }

        # Round-robin matchups
        for i, model_a in enumerate(model_ids):
            for model_b in model_ids[i + 1 :]:
                metric_diffs: dict[str, float] = {}
                a_wins = 0
                for m in metrics:
                    diff = round(model_scores[model_a][m] - model_scores[model_b][m], 4)
                    metric_diffs[m] = diff
                    if diff > 0:
                        a_wins += 1

                winner = model_a if a_wins >= len(metrics) / 2 else model_b
                wins[winner] += 1
                matchups.append(
                    {
                        "model_a": model_a,
                        "model_b": model_b,
                        "winner": winner,
                        "metric_diffs": metric_diffs,
                        "scores_a": model_scores[model_a],
                        "scores_b": model_scores[model_b],
                    }
                )

        rankings = sorted(model_ids, key=lambda mid: wins[mid], reverse=True)
        overall_winner = rankings[0]

        return {
            "matchups": matchups,
            "rankings": rankings,
            "overall_winner": overall_winner,
            "wins": wins,
            # The comparison logic is real; the scores it compared are not.
            "simulated": True,
        }

    @staticmethod
    async def threshold_analysis(
        predictions: list[float],
        ground_truth: list[int],
        thresholds: list[float] | None = None,
    ) -> list[dict[str, float]]:
        """Compute precision/recall/F1/accuracy at each threshold."""
        if thresholds is None:
            thresholds = [round(t * 0.1, 1) for t in range(1, 10)]

        results: list[dict[str, float]] = []
        n = len(predictions)

        for threshold in thresholds:
            tp = fp = tn = fn = 0
            for pred, truth in zip(predictions, ground_truth):
                predicted_label = 1 if pred >= threshold else 0
                if predicted_label == 1 and truth == 1:
                    tp += 1
                elif predicted_label == 1 and truth == 0:
                    fp += 1
                elif predicted_label == 0 and truth == 0:
                    tn += 1
                else:
                    fn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
            accuracy = (tp + tn) / n if n > 0 else 0.0

            results.append(
                {
                    "threshold": threshold,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "accuracy": round(accuracy, 4),
                }
            )

        return results

    @staticmethod
    async def generate_scorecard(
        db: AsyncSession,
        model_id: str,
    ) -> dict[str, Any]:
        """Generate a scorecard summarizing a model's benchmark history."""
        result = await db.execute(
            select(Event).where(Event.type == "benchmark")
        )
        events = result.scalars().all()

        benchmarks: list[dict[str, Any]] = []
        all_scores: dict[str, list[float]] = {}

        for event in events:
            payload = event.payload or {}
            model_ids = payload.get("model_ids", [])
            results = payload.get("results", {})
            if model_id in model_ids and model_id in results:
                scores = results[model_id]
                benchmarks.append(
                    {
                        "benchmark_id": str(event.id),
                        "name": payload.get("name", "unnamed"),
                        "scores": scores,
                    }
                )
                for metric, value in scores.items():
                    all_scores.setdefault(metric, []).append(value)

        avg_scores = {
            metric: round(sum(vals) / len(vals), 4)
            for metric, vals in all_scores.items()
            if vals
        }

        # Identify strengths (metrics >=0.85 avg) and weaknesses (<0.7 avg)
        strengths = [m for m, v in avg_scores.items() if v >= 0.85 and m not in ("latency_ms", "throughput")]
        weaknesses = [m for m, v in avg_scores.items() if v < 0.7 and m not in ("latency_ms", "throughput")]

        # Handle latency/throughput specially
        if "latency_ms" in avg_scores and avg_scores["latency_ms"] < 50:
            strengths.append("low_latency")
        if "latency_ms" in avg_scores and avg_scores["latency_ms"] > 150:
            weaknesses.append("high_latency")

        return {
            "model": model_id,
            "benchmarks": benchmarks,
            "avg_scores": avg_scores,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
