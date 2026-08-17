"""The trust boundary, asserted.

These tests are the regression net for WS-A. The first one in particular is
meant to *fail loudly* the day someone registers a route that does not require
identity: it enumerates the live routing table rather than a hand-maintained
list, so there is nothing to forget to update.

Run:

    cd backend
    pytest tests/test_auth_enforcement.py -v
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth_policy import PUBLIC_METHODS, is_public
from app.core.security import create_access_token, create_refresh_token
from app.main import app

pytestmark = [pytest.mark.anyio, pytest.mark.auth_enforced]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
WORKSPACE_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


def token_for(workspace_id: uuid.UUID, user_id: uuid.UUID | None = None) -> str:
    """Mint a real, signed access token scoped to *workspace_id*."""
    return create_access_token(
        {
            "sub": str(user_id or uuid.uuid4()),
            "workspace_id": str(workspace_id),
        }
    )


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Client that surfaces 500 responses instead of re-raising them.

    Starlette's ServerErrorMiddleware always re-raises after invoking the
    handler, so ``raise_app_exceptions=False`` is what lets us assert on the
    *body* the caller would actually receive.
    """
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _sample_path(route: APIRoute) -> str:
    """Substitute a plausible value for each path parameter."""
    path = route.path
    for param in route.param_convertors:
        convertor = route.param_convertors[param]
        kind = type(convertor).__name__.lower()
        if "uuid" in kind:
            value = str(uuid.uuid4())
        elif "int" in kind or "float" in kind:
            value = "1"
        elif "path" in kind:
            value = "sample/path"
        else:
            value = "sample"
        path = path.replace("{" + param + "}", value)
    return path


def _enumerate_routes() -> list[tuple[str, str, str]]:
    """Return (method, templated path, concrete path) for every API route."""
    entries: list[tuple[str, str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        concrete = _sample_path(route)
        for method in sorted(route.methods or set()):
            if method in PUBLIC_METHODS or method == "HEAD":
                continue
            entries.append((method, route.path, concrete))
    return entries


ALL_ROUTES = _enumerate_routes()


# ---------------------------------------------------------------------------
# 1. The regression net — every route, no token, must be 401 unless allowlisted
# ---------------------------------------------------------------------------


def test_route_table_is_not_empty():
    """Guard the guard: an empty enumeration would make the sweep vacuous."""
    assert len(ALL_ROUTES) > 50, (
        f"only {len(ALL_ROUTES)} routes enumerated — the sweep below would "
        "pass without testing anything"
    )


async def test_every_route_requires_authentication(client):
    """Walk the whole routing table anonymously; everything must 401.

    If this fails with an unexpected path, someone added a route that serves
    data to anonymous callers. Either it is genuinely public — in which case
    add it to ``app.core.auth_policy.PUBLIC_PATHS`` and say why in the diff —
    or the trust boundary just regressed.
    """
    unprotected: list[str] = []

    for method, template, concrete in ALL_ROUTES:
        if is_public(concrete, method):
            continue
        response = await client.request(method, concrete)
        if response.status_code != 401:
            unprotected.append(f"{method} {template} -> {response.status_code}")

    assert not unprotected, (
        "these routes answered an unauthenticated request without 401:\n  "
        + "\n  ".join(unprotected)
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/openapi.json",
        "/docs",
    ],
)
async def test_allowlisted_paths_are_reachable_without_a_token(client, path):
    """The allowlist must actually be open, or login becomes impossible."""
    response = await client.request("GET" if path != "/api/auth/login" else "POST", path)
    assert response.status_code != 401, f"{path} is allowlisted but returned 401"


async def test_options_preflight_is_never_challenged(client):
    """CORS preflights carry no Authorization header by design."""
    response = await client.request(
        "OPTIONS",
        "/api/assets",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code != 401


async def test_garbage_token_is_rejected(client):
    response = await client.get("/api/auth/me", headers=auth("not-a-jwt"))
    assert response.status_code == 401


async def test_refresh_token_cannot_be_used_as_an_access_token(client):
    """A refresh token is a credential for /auth/refresh, not for the API."""
    token = create_refresh_token({"sub": str(uuid.uuid4())})
    response = await client.get("/api/auth/me", headers=auth(token))
    assert response.status_code == 401
    assert "refresh" in response.json()["detail"].lower()


async def test_denial_advertises_the_scheme(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


@pytest.fixture
def open_probe():
    """A route with no auth dependency of its own — like the other 57."""
    path = "/__ws_a_test__/open"

    async def _ok():
        return {"ok": True}

    app.add_api_route(path, _ok, methods=["GET"])
    try:
        yield path
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != path
        ]


async def test_a_route_with_no_dependency_is_still_protected(client, open_probe):
    """The whole point: protection does not come from the route.

    This probe is the shape of the 57 unprotected modules — no
    ``Depends(get_current_user)`` anywhere in sight.
    """
    assert (await client.get(open_probe)).status_code == 401


async def test_auth_required_flag_gates_the_middleware(client, open_probe):
    """AUTH_REQUIRED is the deliberate opt-out; prove it is load-bearing."""
    previous = settings.AUTH_REQUIRED
    settings.AUTH_REQUIRED = False
    try:
        assert (await client.get(open_probe)).status_code == 200
    finally:
        settings.AUTH_REQUIRED = previous

    assert (await client.get(open_probe)).status_code == 401


# ---------------------------------------------------------------------------
# 2. Tenant isolation — the workspace comes from the token, not the caller
# ---------------------------------------------------------------------------

WORKSPACE_PROBE = "/__ws_a_test__/workspace"


@pytest.fixture
def workspace_probe():
    """Register a throwaway route that echoes the resolved workspace.

    Exercising the plumbing needs a handler that consumes it. WS-B owns the
    real routes, so the probe is created and removed here rather than by
    editing a file this workstream does not own.
    """
    from uuid import UUID

    from fastapi import Depends

    from app.core.deps import get_workspace_id

    async def _echo(workspace_id: UUID = Depends(get_workspace_id)):
        return {"workspace_id": str(workspace_id)}

    app.add_api_route(WORKSPACE_PROBE, _echo, methods=["GET"])
    app.router.routes[-1].name = "ws_a_workspace_probe"
    try:
        yield WORKSPACE_PROBE
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != WORKSPACE_PROBE
        ]


async def test_workspace_id_comes_from_the_token(client, workspace_probe):
    response = await client.get(workspace_probe, headers=auth(token_for(WORKSPACE_A)))
    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(WORKSPACE_A)


async def test_token_for_workspace_a_cannot_read_workspace_b(client, workspace_probe):
    """A token minted for A must never resolve to B.

    This is the isolation invariant in its smallest form: whatever the caller
    sends, the workspace the server acts on is the one inside the signed token.
    The request below asks for B in the query string and in a header — both are
    caller-controlled, and both must be ignored.
    """
    token_a = token_for(WORKSPACE_A)

    response = await client.get(
        workspace_probe,
        params={"workspace_id": str(WORKSPACE_B)},
        headers={
            **auth(token_a),
            "X-Workspace-Id": str(WORKSPACE_B),
        },
    )

    assert response.status_code == 200
    resolved = response.json()["workspace_id"]
    assert resolved == str(WORKSPACE_A)
    assert resolved != str(WORKSPACE_B), "tenant isolation breached: caller chose the tenant"

    # ...and the B token still resolves to B, so the check above is not simply
    # a constant being returned.
    response_b = await client.get(workspace_probe, headers=auth(token_for(WORKSPACE_B)))
    assert response_b.json()["workspace_id"] == str(WORKSPACE_B)


async def test_no_hardcoded_default_workspace_leaks_in(client, workspace_probe):
    """The old 00000000-...-0001 fallback must not reappear anywhere."""
    response = await client.get(workspace_probe, headers=auth(token_for(WORKSPACE_A)))
    assert response.json()["workspace_id"] != "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 3. Middleware is live — headers prove it
# ---------------------------------------------------------------------------


async def test_request_id_header_is_present(client):
    """RequestIDMiddleware runs: every response is traceable."""
    response = await client.get("/api/health")
    assert response.headers.get("X-Request-ID"), "X-Request-ID missing — middleware is off"
    uuid.UUID(response.headers["X-Request-ID"])  # well-formed


async def test_request_id_is_echoed_when_supplied(client):
    supplied = str(uuid.uuid4())
    response = await client.get("/api/health", headers={"X-Request-ID": supplied})
    assert response.headers["X-Request-ID"] == supplied


async def test_request_id_is_unique_per_request(client):
    first = await client.get("/api/health")
    second = await client.get("/api/health")
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


async def test_timing_header_is_present(client):
    """TimingMiddleware runs and reports a plausible duration."""
    response = await client.get("/api/health")
    raw = response.headers.get("X-Process-Time")
    assert raw is not None, "X-Process-Time missing — middleware is off"
    assert float(raw) >= 0


async def test_middleware_wraps_denials_too(client):
    """A 401 is still stamped: you can trace a rejected request."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Process-Time")


def test_audit_middleware_is_installed():
    """The compliance claim needs the class in the stack, not just on disk."""
    from app.middleware.audit import AuditMiddleware

    installed = {m.cls for m in app.user_middleware}
    assert AuditMiddleware in installed


def test_all_four_middlewares_are_installed():
    from starlette.middleware.gzip import GZipMiddleware

    from app.middleware.audit import AuditMiddleware
    from app.middleware.auth import AuthenticationMiddleware
    from app.middleware.request_id import RequestIDMiddleware
    from app.middleware.timing import TimingMiddleware

    installed = {m.cls for m in app.user_middleware}
    for cls in (
        RequestIDMiddleware,
        TimingMiddleware,
        AuditMiddleware,
        GZipMiddleware,
        AuthenticationMiddleware,
    ):
        assert cls in installed, f"{cls.__name__} is not in the middleware stack"


# ---------------------------------------------------------------------------
# 4. 500 responses do not leak
# ---------------------------------------------------------------------------

BOOM_PATH = "/__ws_a_test__/boom"
SECRET_IN_EXCEPTION = "postgresql://visionaudio:hunter2@db:5432/visionaudioforge"


@pytest.fixture
def exploding_route():
    async def _boom():
        raise RuntimeError(f"connection refused for {SECRET_IN_EXCEPTION}")

    app.add_api_route(BOOM_PATH, _boom, methods=["GET"])
    try:
        yield BOOM_PATH
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != BOOM_PATH
        ]


async def test_500_body_does_not_contain_the_exception_text(client, exploding_route):
    response = await client.get(exploding_route, headers=auth(token_for(WORKSPACE_A)))

    assert response.status_code == 500
    body = response.text
    assert SECRET_IN_EXCEPTION not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    assert response.json()["detail"] == "Internal server error"


async def test_500_body_carries_a_request_id(client, exploding_route):
    """The caller gets something to quote; the detail stays in the log."""
    response = await client.get(exploding_route, headers=auth(token_for(WORKSPACE_A)))

    payload = response.json()
    assert payload["request_id"]
    uuid.UUID(payload["request_id"])
    assert response.headers.get("X-Request-ID") == payload["request_id"]


async def test_500_request_id_matches_the_supplied_one(client, exploding_route):
    supplied = str(uuid.uuid4())
    response = await client.get(
        exploding_route,
        headers={**auth(token_for(WORKSPACE_A)), "X-Request-ID": supplied},
    )
    assert response.json()["request_id"] == supplied


async def test_debug_errors_flag_restores_the_verbose_form(client, exploding_route):
    """Verbose diagnostics stay available — behind a flag that defaults off."""
    assert settings.DEBUG_ERRORS is False, "DEBUG_ERRORS must default to off"

    settings.DEBUG_ERRORS = True
    try:
        response = await client.get(exploding_route, headers=auth(token_for(WORKSPACE_A)))
    finally:
        settings.DEBUG_ERRORS = False

    payload = response.json()
    assert "RuntimeError" in payload["exception"]
    assert payload["traceback"]


# ---------------------------------------------------------------------------
# 5. WebSockets — BaseHTTPMiddleware would have skipped these entirely
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_websocket_handshake_without_a_token_is_refused():
    """Live capture and copilot streams are behind the same boundary.

    ``BaseHTTPMiddleware`` passes websocket scopes straight through, which is
    one of the reasons the auth layer is raw ASGI.
    """
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    with TestClient(app) as tc:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with tc.websocket_connect("/ws/live/stream/abc"):
                pass

    assert excinfo.value.code == 1008


def test_websocket_token_is_read_from_the_query_string():
    """Browsers cannot set headers on a WebSocket, so ?token= is the way in."""
    from app.middleware.auth import _websocket_query_token

    ws_scope = {"type": "websocket", "query_string": b"token=abc.def.ghi&x=1"}
    assert _websocket_query_token(ws_scope) == "abc.def.ghi"

    # ...and never for plain HTTP: URLs land in access logs and Referer.
    http_scope = {"type": "http", "query_string": b"token=abc.def.ghi"}
    assert _websocket_query_token(http_scope) is None
