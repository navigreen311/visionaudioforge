"""Prometheus metrics definitions."""

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

ACTIVE_CONNECTIONS = Gauge(
    "ws_active_connections",
    "Active WebSocket connections",
)

INFERENCE_QUEUE = Gauge(
    "inference_queue_depth",
    "Inference job queue depth",
)
