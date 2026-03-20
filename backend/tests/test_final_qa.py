"""Final QA tests — verify app loads, routes registered, version correct, CORS configured."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app, raise_server_exceptions=False)


def test_app_starts():
    """App object must be importable and not None."""
    assert app is not None


def test_all_routes_registered():
    """Platform must expose >= 300 routes."""
    route_count = len(app.routes)
    assert route_count >= 300, f"Expected >= 300 routes, got {route_count}"


def test_health_endpoint():
    """GET /api/health must return 200."""
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_no_501_on_core_endpoints():
    """Core endpoints must not return 501 Not Implemented."""
    endpoints = [
        "/api/health",
        "/api/registry/models",
        "/api/datasets",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code != 501, f"{ep} returned 501"


def test_version_is_1_0_0():
    """App version must be 1.0.0."""
    assert app.version == "1.0.0"


def test_cors_configured():
    """CORS middleware must be present."""
    middleware_classes = [type(m).__name__ for m in app.user_middleware]
    # FastAPI stores CORS as user_middleware entries; check via cls attribute
    cors_found = any("CORS" in str(m.cls) for m in app.user_middleware)
    assert cors_found, f"CORS middleware not found in {middleware_classes}"


def test_models_loadable():
    """All model modules must be importable."""
    from app.models import base  # noqa: F401
    from app.models.semantic_memory import MemoryScope, SemanticMemory  # noqa: F401

    assert SemanticMemory.__tablename__ == "semantic_memories"
    assert MemoryScope.workspace == "workspace"
