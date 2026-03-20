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

# ---------------------------------------------------------------------------
# Enhanced metrics — M9 Observability + SRE
# ---------------------------------------------------------------------------

MODEL_INFERENCE_DURATION = Histogram(
    "model_inference_duration_seconds",
    "Model inference time",
    ["model_name"],
)

PIPELINE_RUN_DURATION = Histogram(
    "pipeline_run_duration_seconds",
    "Pipeline run time",
    ["pipeline_id"],
)

ALERT_RESPONSE_TIME = Histogram(
    "alert_response_time_seconds",
    "Time to acknowledge alert",
)

STORAGE_USAGE_BYTES = Gauge(
    "storage_usage_bytes",
    "Total storage used",
    ["workspace_id"],
)

ERROR_COUNT = Counter(
    "errors_total",
    "Total errors",
    ["type", "endpoint"],
)
