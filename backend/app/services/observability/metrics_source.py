"""Read measured values out of the live Prometheus registry.

Everything in this module reports what was actually observed in this process.
When no samples have been recorded the helpers say so explicitly (``None`` /
``observed=False``) rather than inventing a plausible-looking number — an
unmeasured metric must never be presentable as a measurement.

Note that ``app.core.metrics`` currently defines the collectors but nothing
increments them yet, so most of these will report "not observed" until request
instrumentation is wired up. That is the honest answer, and callers are
expected to surface it as "unknown" in the UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from prometheus_client import REGISTRY

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Measurement:
    """A value that may or may not have been observed."""

    value: float | None
    observed: bool
    sample_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "observed": self.observed,
            "sample_count": self.sample_count,
        }


UNOBSERVED = Measurement(value=None, observed=False, sample_count=0)


def _iter_samples(metric_name: str):
    """Yield prometheus samples whose name starts with *metric_name*."""
    try:
        for family in REGISTRY.collect():
            for sample in family.samples:
                if sample.name.startswith(metric_name):
                    yield sample
    except Exception:  # pragma: no cover - registry access should not break callers
        logger.exception("Failed to read Prometheus registry")
        return


def request_totals() -> tuple[int, int]:
    """Return (total_requests, error_requests) observed by http_requests_total.

    Errors are responses with a 5xx status label.
    """
    total = 0
    errors = 0
    for sample in _iter_samples("http_requests_total"):
        if not sample.name.endswith("_total"):
            continue
        count = int(sample.value)
        total += count
        status = str(sample.labels.get("status", ""))
        if status.startswith("5"):
            errors += count
    return total, errors


def error_rate() -> Measurement:
    """Fraction of observed requests that returned 5xx."""
    total, errors = request_totals()
    if total == 0:
        return UNOBSERVED
    return Measurement(value=errors / total, observed=True, sample_count=total)


def average_request_latency_ms() -> Measurement:
    """Mean HTTP request latency in milliseconds, from the duration histogram."""
    total_seconds = 0.0
    count = 0
    for sample in _iter_samples("http_request_duration_seconds"):
        if sample.name.endswith("_sum"):
            total_seconds += float(sample.value)
        elif sample.name.endswith("_count"):
            count += int(sample.value)
    if count == 0:
        return UNOBSERVED
    return Measurement(value=(total_seconds / count) * 1000.0, observed=True, sample_count=count)


def counter_by_label(metric_name: str, label: str) -> dict[str, int]:
    """Sum a labelled counter, grouped by one label value.

    Returns an empty dict when nothing has been counted — an empty breakdown is
    a truthful "no errors observed", not a placeholder.
    """
    totals: dict[str, int] = {}
    for sample in _iter_samples(metric_name):
        if not sample.name.endswith("_total"):
            continue
        key = sample.labels.get(label)
        if key is None:
            continue
        totals[key] = totals.get(key, 0) + int(sample.value)
    return totals


def gauge_value(metric_name: str) -> Measurement:
    """Current value of a simple (unlabelled) gauge."""
    for sample in _iter_samples(metric_name):
        if sample.name == metric_name:
            return Measurement(value=float(sample.value), observed=True, sample_count=1)
    return UNOBSERVED


def histogram_average(metric_name: str, scale: float = 1.0) -> Measurement:
    """Mean of a histogram, multiplied by *scale* (e.g. 1000 for s -> ms)."""
    total = 0.0
    count = 0
    for sample in _iter_samples(metric_name):
        if sample.name == f"{metric_name}_sum":
            total += float(sample.value)
        elif sample.name == f"{metric_name}_count":
            count += int(sample.value)
    if count == 0:
        return UNOBSERVED
    return Measurement(value=(total / count) * scale, observed=True, sample_count=count)
