"""ValidationService — calibration analysis, drift detection, uncertainty estimation,
model cards, and audit trails."""

from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_registry import ModelRecord


class ValidationService:
    """Core validation and trust utilities for ML models."""

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    @staticmethod
    async def calibration_analysis(
        predictions: list[float],
        ground_truth: list[int],
        n_bins: int = 10,
    ) -> dict:
        """Compute reliability-diagram bins, ECE, and MCE.

        ECE = sum(|accuracy_i - confidence_i| * n_i / N)
        MCE = max(|accuracy_i - confidence_i|)
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("predictions and ground_truth must have the same length")

        n = len(predictions)
        bin_width = 1.0 / n_bins
        bins: list[dict] = []
        ece = 0.0
        mce = 0.0

        for i in range(n_bins):
            bin_start = i * bin_width
            bin_end = (i + 1) * bin_width

            # Collect samples whose predicted confidence falls in this bin
            indices = [
                j
                for j, p in enumerate(predictions)
                if (bin_start <= p < bin_end) or (i == n_bins - 1 and p == bin_end)
            ]
            count = len(indices)

            if count == 0:
                bins.append(
                    {
                        "bin_start": round(bin_start, 4),
                        "bin_end": round(bin_end, 4),
                        "avg_confidence": 0.0,
                        "accuracy": 0.0,
                        "count": 0,
                    }
                )
                continue

            avg_conf = sum(predictions[j] for j in indices) / count
            accuracy = sum(ground_truth[j] for j in indices) / count

            gap = abs(accuracy - avg_conf)
            ece += gap * count / n
            mce = max(mce, gap)

            bins.append(
                {
                    "bin_start": round(bin_start, 4),
                    "bin_end": round(bin_end, 4),
                    "avg_confidence": round(avg_conf, 4),
                    "accuracy": round(accuracy, 4),
                    "count": count,
                }
            )

        is_calibrated = ece < 0.05  # industry-standard threshold

        # --- Extended classification metrics (VA1) ---
        threshold = 0.5
        tp = sum(
            1 for p, g in zip(predictions, ground_truth) if p >= threshold and g == 1
        )
        fp = sum(
            1 for p, g in zip(predictions, ground_truth) if p >= threshold and g == 0
        )
        tn = sum(
            1 for p, g in zip(predictions, ground_truth) if p < threshold and g == 0
        )
        fn = sum(
            1 for p, g in zip(predictions, ground_truth) if p < threshold and g == 1
        )

        accuracy = (tp + tn) / n if n > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        # Approximate AUC-ROC via trapezoidal rule (simple ranked approach)
        # Sort by descending prediction score and compute TPR/FPR curve
        total_pos = sum(ground_truth)
        total_neg = n - total_pos
        if total_pos > 0 and total_neg > 0:
            sorted_pairs = sorted(
                zip(predictions, ground_truth), key=lambda x: -x[0]
            )
            auc_roc = 0.0
            tp_count = 0
            fp_count = 0
            prev_fpr = 0.0
            prev_tpr = 0.0
            for pred_val, gt_val in sorted_pairs:
                if gt_val == 1:
                    tp_count += 1
                else:
                    fp_count += 1
                fpr = fp_count / total_neg
                tpr = tp_count / total_pos
                auc_roc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2
                prev_fpr = fpr
                prev_tpr = tpr
        else:
            auc_roc = 0.0

        return {
            "bins": bins,
            "ece": round(ece, 6),
            "mce": round(mce, 6),
            "is_calibrated": is_calibrated,
            "accuracy": round(accuracy, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "auc_roc": round(auc_roc, 6),
        }

    # ------------------------------------------------------------------
    # Drift Detection
    # ------------------------------------------------------------------

    @staticmethod
    async def drift_detection(
        reference_stats: dict,
        current_stats: dict,
    ) -> dict:
        """Compare feature distributions between reference and current data.

        Drift is detected when |current_mean - ref_mean| > 2 * ref_std
        for any feature.
        """
        drifted_features: list[str] = []
        drift_scores: list[float] = []

        for feature in reference_stats:
            if feature not in current_stats:
                continue

            ref = reference_stats[feature]
            cur = current_stats[feature]
            ref_mean = ref.get("mean", 0.0)
            ref_std = ref.get("std", 1.0)
            cur_mean = cur.get("mean", 0.0)

            if ref_std == 0:
                ref_std = 1e-8  # avoid division by zero

            diff = abs(cur_mean - ref_mean)
            score = diff / ref_std  # z-score-like drift magnitude

            drift_scores.append(score)
            if diff > 2 * ref_std:
                drifted_features.append(feature)

        drift_detected = len(drifted_features) > 0
        overall_score = max(drift_scores) if drift_scores else 0.0

        if not drift_detected:
            recommendation = "No significant drift detected. Continue monitoring."
        elif len(drifted_features) <= 2:
            recommendation = (
                f"Moderate drift in {', '.join(drifted_features)}. "
                "Consider retraining with recent data."
            )
        else:
            recommendation = (
                f"Significant drift in {len(drifted_features)} features. "
                "Immediate retraining recommended."
            )

        return {
            "drift_detected": drift_detected,
            "drift_score": round(overall_score, 4),
            "drifted_features": drifted_features,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Uncertainty Estimation
    # ------------------------------------------------------------------

    @staticmethod
    async def uncertainty_estimation(
        predictions: list[list[float]],
    ) -> dict:
        """Compute per-sample entropy and flag uncertain predictions.

        Entropy = -sum(p * log(p)).  Uncertain when entropy > 0.5 * max_entropy.
        """
        if not predictions:
            return {
                "per_sample": [],
                "avg_entropy": 0.0,
                "uncertain_count": 0,
                "uncertain_pct": 0.0,
            }

        n_classes = len(predictions[0])
        max_entropy = math.log(n_classes) if n_classes > 1 else 1.0
        threshold = 0.5 * max_entropy

        per_sample: list[dict] = []
        total_entropy = 0.0
        uncertain_count = 0

        for probs in predictions:
            entropy = 0.0
            for p in probs:
                if p > 0:
                    entropy -= p * math.log(p)

            pred_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
            confidence = probs[pred_idx]
            is_uncertain = entropy > threshold

            if is_uncertain:
                uncertain_count += 1
            total_entropy += entropy

            per_sample.append(
                {
                    "prediction": pred_idx,
                    "confidence": round(confidence, 4),
                    "entropy": round(entropy, 4),
                    "is_uncertain": is_uncertain,
                }
            )

        n = len(predictions)
        return {
            "per_sample": per_sample,
            "avg_entropy": round(total_entropy / n, 4),
            "uncertain_count": uncertain_count,
            "uncertain_pct": round(uncertain_count / n * 100, 2),
        }

    # ------------------------------------------------------------------
    # Model Card
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_model_card(db: AsyncSession, model_id: UUID) -> dict:
        """Build a model-card summary for a registered model."""
        result = await db.execute(
            select(ModelRecord).where(ModelRecord.id == model_id)
        )
        record = result.scalar_one_or_none()

        if record is None:
            return {"error": f"Model {model_id} not found"}

        metrics = record.metrics or {}

        return {
            "model_name": record.name,
            "version": record.version,
            "description": f"{record.name} v{record.version} — {record.backbone or 'custom'} backbone.",
            "metrics": metrics,
            "intended_use": "Production inference on vision/audio data within the VisionAudioForge platform.",
            "limitations": (
                "Performance may degrade on out-of-distribution data. "
                "Evaluate calibration and drift before deploying to new domains."
            ),
            "training_data": metrics.get("training_data", "Not specified"),
            "evaluation_results": {
                k: v for k, v in metrics.items() if k != "training_data"
            },
            "ethical_considerations": (
                "Ensure representative evaluation across demographic groups. "
                "Monitor for fairness and bias before production deployment."
            ),
        }

    # ------------------------------------------------------------------
    # Audit Trail
    # ------------------------------------------------------------------

    @staticmethod
    async def audit_trail(
        db: AsyncSession, model_id: UUID, limit: int = 50
    ) -> list[dict]:
        """Return recent inference / status-change events for a model.

        NOTE: Full audit logging requires an AuditEvent table. For V1 we
        return a summary derived from the model record itself.
        """
        result = await db.execute(
            select(ModelRecord).where(ModelRecord.id == model_id)
        )
        record = result.scalar_one_or_none()

        if record is None:
            return []

        # V1: synthetic audit trail from available metadata
        events: list[dict] = [
            {
                "event": "model_registered",
                "model_id": str(record.id),
                "model_name": record.name,
                "version": record.version,
                "status": record.status,
                "timestamp": str(record.created_at),
            }
        ]

        if str(record.created_at) != str(record.updated_at):
            events.append(
                {
                    "event": "status_change",
                    "model_id": str(record.id),
                    "status": record.status,
                    "timestamp": str(record.updated_at),
                }
            )

        return events[:limit]
