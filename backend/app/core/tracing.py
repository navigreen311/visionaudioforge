"""Distributed tracing service using OpenTelemetry."""

from __future__ import annotations

import time
import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports – OpenTelemetry packages are optional at runtime so the rest
# of the application can still start when they are not installed.
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    _HAS_OTEL = True
except ImportError:  # pragma: no cover
    _HAS_OTEL = False
    trace = None  # type: ignore[assignment]

# Stub for future Jaeger exporter
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter  # type: ignore[import-untyped]

    _HAS_JAEGER = True
except ImportError:
    _HAS_JAEGER = False


class TracingService:
    """Centralised distributed-tracing helper wrapping OpenTelemetry."""

    _provider: Any = None
    _tracer: Any = None
    _initialised: bool = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    @classmethod
    def setup_tracing(
        cls,
        service_name: str = "visionaudioforge-api",
        *,
        use_jaeger: bool = False,
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
    ) -> None:
        """Configure the OpenTelemetry TracerProvider.

        V1 uses ``ConsoleSpanExporter`` by default.  When *use_jaeger* is
        ``True`` **and** the Jaeger exporter package is installed, spans are
        forwarded to a Jaeger agent instead.
        """
        if cls._initialised:
            return

        if not _HAS_OTEL:
            logger.warning(
                "opentelemetry-sdk is not installed – tracing disabled"
            )
            return

        cls._provider = TracerProvider()

        # Exporter selection
        if use_jaeger and _HAS_JAEGER:
            exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            logger.info("Tracing: Jaeger exporter → %s:%s", jaeger_host, jaeger_port)
        else:
            exporter = ConsoleSpanExporter()
            logger.info("Tracing: ConsoleSpanExporter (V1 default)")

        cls._provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(cls._provider)
        cls._initialised = True

    # ------------------------------------------------------------------
    # Tracer access
    # ------------------------------------------------------------------

    @classmethod
    def get_tracer(cls, name: str = "vaf") -> Any:
        """Return a named ``Tracer`` instance."""
        if not cls._initialised:
            cls.setup_tracing()

        if not _HAS_OTEL:
            return _NoOpTracer()

        if cls._tracer is None or cls._tracer.instrumentation_info.name != name:
            cls._tracer = trace.get_tracer(name)
        return cls._tracer

    # ------------------------------------------------------------------
    # Middleware helper
    # ------------------------------------------------------------------

    @classmethod
    async def trace_request(cls, request: Any, call_next: Any) -> Any:
        """ASGI middleware that wraps every HTTP request in a span.

        Usage with FastAPI::

            app.middleware("http")(TracingService.trace_request)
        """
        tracer = cls.get_tracer()
        method = request.method
        path = request.url.path
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None

        span_ctx = tracer.start_as_current_span(
            f"HTTP {method} {path}",
            attributes={
                "http.method": method,
                "http.path": path,
            },
        )

        start = time.perf_counter()
        with span_ctx as span:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("duration_ms", round(duration_ms, 2))
            if user_id is not None:
                span.set_attribute("user_id", str(user_id))

        return response

    # ------------------------------------------------------------------
    # Context managers for child spans
    # ------------------------------------------------------------------

    @classmethod
    @contextmanager
    def trace_db_query(cls, query_name: str) -> Generator[Any, None, None]:
        """Create a child span for a database operation."""
        tracer = cls.get_tracer()
        with tracer.start_as_current_span(
            f"DB {query_name}",
            attributes={"db.operation": query_name},
        ) as span:
            start = time.perf_counter()
            try:
                yield span
            finally:
                span.set_attribute(
                    "duration_ms",
                    round((time.perf_counter() - start) * 1000, 2),
                )

    @classmethod
    @contextmanager
    def trace_inference(
        cls, model_name: str, input_size: int
    ) -> Generator[Any, None, None]:
        """Create a child span for an ML inference call."""
        tracer = cls.get_tracer()
        with tracer.start_as_current_span(
            f"Inference {model_name}",
            attributes={
                "ml.model_name": model_name,
                "ml.input_size": input_size,
            },
        ) as span:
            start = time.perf_counter()
            try:
                yield span
            finally:
                span.set_attribute(
                    "duration_ms",
                    round((time.perf_counter() - start) * 1000, 2),
                )

    @classmethod
    @contextmanager
    def trace_external_call(
        cls, service_name: str, endpoint: str
    ) -> Generator[Any, None, None]:
        """Create a child span for an external API call."""
        tracer = cls.get_tracer()
        with tracer.start_as_current_span(
            f"External {service_name}",
            attributes={
                "external.service": service_name,
                "external.endpoint": endpoint,
            },
        ) as span:
            start = time.perf_counter()
            try:
                yield span
            finally:
                span.set_attribute(
                    "duration_ms",
                    round((time.perf_counter() - start) * 1000, 2),
                )


# ---------------------------------------------------------------------------
# No-op fallback when OpenTelemetry is unavailable
# ---------------------------------------------------------------------------


class _NoOpSpan:
    """Minimal stand-in when OTel is missing."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: D401
        pass

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _NoOpTracer:
    """Minimal tracer that does nothing."""

    class instrumentation_info:  # noqa: N801
        name = "noop"

    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()
