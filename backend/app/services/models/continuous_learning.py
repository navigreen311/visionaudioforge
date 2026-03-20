"""Continuous / active learning: feedback capture and retraining triggers."""

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ContinuousLearningService:
    """Manages the human-in-the-loop feedback cycle for deployed models.

    V1 stores feedback in-memory; production would persist to a database.
    """

    def __init__(self) -> None:
        # model_id → list of feedback events
        self._feedback_store: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Capture feedback
    # ------------------------------------------------------------------

    def capture_feedback(
        self,
        model_id: str,
        input_data: Any,
        predicted: str,
        corrected: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a single correction event."""
        event = {
            "event_id": str(uuid.uuid4()),
            "model_id": model_id,
            "predicted": predicted,
            "corrected": corrected,
            "is_correction": predicted != corrected,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedback_store.setdefault(model_id, []).append(event)
        logger.info("Feedback captured for model %s (event %s)", model_id, event["event_id"])
        return event

    # ------------------------------------------------------------------
    # Feedback queue status
    # ------------------------------------------------------------------

    def get_feedback_queue(
        self,
        model_id: str,
        min_count: int = 50,
    ) -> dict[str, Any]:
        """Report whether enough feedback has been collected to trigger retraining."""
        events = self._feedback_store.get(model_id, [])
        corrections = [e for e in events if e.get("is_correction")]
        correction_rate = len(corrections) / max(len(events), 1)

        class_dist: dict[str, int] = dict(Counter(e["corrected"] for e in events))

        return {
            "ready_to_retrain": len(events) >= min_count,
            "feedback_count": len(events),
            "correction_rate": round(correction_rate, 4),
            "class_distribution": class_dist,
        }

    # ------------------------------------------------------------------
    # Trigger retraining (V1 – stub)
    # ------------------------------------------------------------------

    def trigger_retraining(
        self,
        model_id: str,
        feedback_data: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Initiate a retraining job (V1: logs intent, real work deferred to Celery)."""
        job_id = str(uuid.uuid4())
        count = len(feedback_data) if feedback_data else 0
        logger.info("Retraining requested for model %s – %d feedback items (job %s)", model_id, count, job_id)
        return {
            "job_id": job_id,
            "strategy": "incremental_finetune",
            "note": "Retraining job queued (V1: Celery task placeholder). Real execution in V2.",
        }

    # ------------------------------------------------------------------
    # Catastrophic-forgetting check
    # ------------------------------------------------------------------

    @staticmethod
    def catastrophic_forgetting_check(
        old_metrics: dict[str, float],
        new_metrics: dict[str, float],
        threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Compare per-class metrics before/after retraining.

        Flags any class whose accuracy dropped by more than *threshold*.
        """
        degraded: list[str] = []
        max_deg = 0.0

        for cls_name, old_val in old_metrics.items():
            new_val = new_metrics.get(cls_name, 0.0)
            drop = old_val - new_val
            if drop > threshold:
                degraded.append(cls_name)
            max_deg = max(max_deg, drop)

        return {
            "safe_to_deploy": len(degraded) == 0,
            "degraded_classes": degraded,
            "max_degradation": round(max_deg, 4),
        }
