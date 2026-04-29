"""Test fixture that mounts the WS11 intel routers in isolation.

WS10 owns ``app/api/router.py`` and ``vaf_v1/__init__.py``, so this branch
must not touch the global wiring. To keep our tests self-sufficient, we
build a fresh FastAPI app, mount our four routers directly, and override
the auth dependency with a no-op. After WS10 merges, the production wire-
up will live in ``vaf_v1/__init__.py`` and these fixtures stay only as
test scaffolding.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.vaf_v1 import meeting, sentiment, translate, vision
from app.api.routes.vaf_v1._auth_shim import vaf_auth

from ._test_auth import noop_vaf_auth


def build_intel_app() -> FastAPI:
    """Construct an isolated FastAPI app with only the WS11 routers."""
    app = FastAPI(title="VAF v1 Intel Endpoints (WS11 test app)")
    app.include_router(sentiment.router)
    app.include_router(meeting.router)
    app.include_router(vision.router)
    app.include_router(translate.router)

    # Override the bearer-token gate so tests don't need real credentials.
    app.dependency_overrides[vaf_auth] = noop_vaf_auth
    return app


def build_intel_client() -> TestClient:
    """Synchronous TestClient for the isolated intel app."""
    return TestClient(build_intel_app())
