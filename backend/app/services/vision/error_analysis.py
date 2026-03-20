"""Systematic error analysis for classification models.

Provides confusion matrix computation, per-class and overall metrics,
top-confusion identification, and consolidated quality reports.
"""

from __future__ import annotations

import numpy as np


def compute_confusion_matrix(
    y_true: list[str],
    y_pred: list[str],
    classes: list[str],
) -> np.ndarray:
    """Build a confusion matrix (rows=true, cols=predicted).

    Args:
        y_true: Ground-truth labels.
        y_pred: Predicted labels.
        classes: Ordered list of class names.

    Returns:
        np.ndarray of shape (n_classes, n_classes).
    """
    n = len(classes)
    idx = {c: i for i, c in enumerate(classes)}
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            cm[idx[t], idx[p]] += 1
    return cm


def class_level_metrics(
    cm: np.ndarray,
    class_names: list[str],
) -> list[dict]:
    """Per-class precision, recall, F1, and support from a confusion matrix.

    Returns:
        List of dicts with keys: class, precision, recall, f1, support.
    """
    metrics: list[dict] = []
    for i, name in enumerate(class_names):
        tp = cm[i, i]
        support = int(cm[i, :].sum())
        pred_total = int(cm[:, i].sum())

        precision = float(tp / pred_total) if pred_total > 0 else 0.0
        recall = float(tp / support) if support > 0 else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        metrics.append(
            {
                "class": name,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": support,
            }
        )
    return metrics


def overall_metrics(cm: np.ndarray) -> dict:
    """Macro-averaged accuracy, precision, recall, and F1.

    Returns:
        Dict with accuracy, macro_precision, macro_recall, macro_f1.
    """
    n = cm.shape[0]
    total = int(cm.sum())
    correct = int(np.trace(cm))
    accuracy = correct / total if total > 0 else 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    for i in range(n):
        tp = cm[i, i]
        pred_total = cm[:, i].sum()
        support = cm[i, :].sum()
        precisions.append(float(tp / pred_total) if pred_total > 0 else 0.0)
        recalls.append(float(tp / support) if support > 0 else 0.0)

    macro_p = float(np.mean(precisions))
    macro_r = float(np.mean(recalls))
    macro_f1 = (
        2.0 * macro_p * macro_r / (macro_p + macro_r)
        if (macro_p + macro_r) > 0
        else 0.0
    )

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
    }


def identify_top_confusions(
    cm: np.ndarray,
    class_names: list[str],
    top_k: int = 5,
) -> list[dict]:
    """Find the most frequent misclassifications.

    Returns:
        Sorted list (descending by count) of dicts with
        true_class, predicted_class, count.
    """
    confusions: list[dict] = []
    n = cm.shape[0]
    for i in range(n):
        for j in range(n):
            if i != j and cm[i, j] > 0:
                confusions.append(
                    {
                        "true_class": class_names[i],
                        "predicted_class": class_names[j],
                        "count": int(cm[i, j]),
                    }
                )
    confusions.sort(key=lambda x: x["count"], reverse=True)
    return confusions[:top_k]


def generate_quality_report(
    y_true: list[str],
    y_pred: list[str],
    class_names: list[str],
) -> dict:
    """Consolidated quality report combining all error-analysis utilities.

    Returns:
        Dict with confusion_matrix, per_class, overall, top_confusions,
        total_samples, and error_rate.
    """
    cm = compute_confusion_matrix(y_true, y_pred, class_names)
    total = int(cm.sum())
    correct = int(np.trace(cm))
    error_rate = 1.0 - (correct / total) if total > 0 else 0.0

    return {
        "confusion_matrix": cm.tolist(),
        "per_class": class_level_metrics(cm, class_names),
        "overall": overall_metrics(cm),
        "top_confusions": identify_top_confusions(cm, class_names),
        "total_samples": total,
        "error_rate": round(error_rate, 4),
    }
