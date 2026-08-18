"""The audit trail actually writes rows.

This is the test that was missing. AuditMiddleware ran on every request for the
entire life of the project and wrote nothing: it constructed ``AuditLog`` with
``resource_type=`` and ``ip_address=``, which are not columns, and never passed
the NOT NULL ``workspace_id``. Because the write is fire-and-forget the
``TypeError`` only ever reached a log line, so every existing test — and the
running application — looked perfectly healthy.

The decisive assertion here is therefore not "the middleware ran" but "the row
that would be committed is constructible against the real model". Anything
weaker reproduces the original blind spot.

Run:

    cd backend
    pytest tests/test_audit_middleware.py -v
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.middleware import audit as audit_module
from app.models.audit_log import AuditLog

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def captured(monkeypatch):
    """Capture rows instead of committing them, keeping the real model."""
    rows: list[AuditLog] = []

    class _Session:
        def __init__(self):
            self.committed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def add(self, obj):
            rows.append(obj)

        async def commit(self):
            self.committed = True

    monkeypatch.setattr(
        "app.database.async_session_factory", lambda: _Session(), raising=False
    )
    return rows


async def drain() -> None:
    """Let the fire-and-forget audit tasks finish."""
    for _ in range(50):
        if not audit_module._pending:
            return
        await asyncio.sleep(0.01)


def make_scope(**overrides):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/assets",
        "headers": [],
        "client": ("10.0.0.7", 51234),
        "state": {},
    }
    scope.update(overrides)
    return scope


async def run_middleware(scope, status: int = 200) -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent = []

    async def send(message):
        sent.append(message)

    await audit_module.AuditMiddleware(app)(scope, lambda: None, send)
    await drain()


# ---------------------------------------------------------------------------
# The bug
# ---------------------------------------------------------------------------


async def test_authenticated_request_writes_a_row(captured, monkeypatch):
    """The whole point: a row reaches the session, built from real columns."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    scope = make_scope(
        state={"workspace_id": workspace_id, "user_id": user_id, "auth_method": "jwt"}
    )

    await run_middleware(scope, status=201)

    assert len(captured) == 1, "audit middleware wrote no row"
    row = captured[0]
    assert isinstance(row, AuditLog)
    assert row.workspace_id == workspace_id
    assert row.user_id == user_id
    assert row.action == "http.get"
    assert row.resource == "/api/assets"


async def test_row_only_uses_columns_the_model_declares(captured, monkeypatch):
    """Guards the exact failure: a stray kwarg raises inside a background task.

    ``AuditLog(resource_type=...)`` raises TypeError in SQLAlchemy's declarative
    constructor. Constructing through the real model — rather than a mock — is
    what makes this test capable of failing.
    """
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    scope = make_scope(state={"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()})
    await run_middleware(scope)

    assert captured, "no row written"
    declared = set(AuditLog.__table__.columns.keys())
    for name in ("workspace_id", "action", "resource", "payload", "user_id"):
        assert name in declared

    # The names that used to be passed and do not exist.
    assert "resource_type" not in declared
    assert "ip_address" not in declared


async def test_payload_carries_the_request_detail(captured, monkeypatch):
    """ip_address had no column; that detail belongs in the JSON payload."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    scope = make_scope(
        method="DELETE",
        path="/api/assets/123",
        state={
            "workspace_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "request_id": "req-abc",
        },
    )
    await run_middleware(scope, status=204)

    payload = captured[0].payload
    assert payload["method"] == "DELETE"
    assert payload["status_code"] == 204
    assert payload["ip"] == "10.0.0.7"
    assert payload["request_id"] == "req-abc"


async def test_forwarded_ip_wins_over_the_socket_peer(captured, monkeypatch):
    """Behind nginx the socket peer is the proxy for every request."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    scope = make_scope(
        headers=[(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")],
        state={"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()},
    )
    await run_middleware(scope)

    assert captured[0].payload["ip"] == "203.0.113.9"


async def test_long_paths_are_truncated_to_the_column_width(captured, monkeypatch):
    """resource is String(200); an over-long path would fail the insert."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    scope = make_scope(
        path="/api/" + "x" * 400,
        state={"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()},
    )
    await run_middleware(scope)

    assert len(captured[0].resource) == audit_module.RESOURCE_MAX_LEN


# ---------------------------------------------------------------------------
# Unauthenticated events — the case the NOT NULL constraint used to forbid
# ---------------------------------------------------------------------------


async def test_unauthenticated_request_is_recorded_with_a_null_workspace(
    captured, monkeypatch
):
    """The inverse of the old behaviour, and the point of migration 017.

    While audit_logs.workspace_id was NOT NULL these events could not be
    stored, so the middleware dropped them. They are now recorded unattributed.
    """
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    await run_middleware(make_scope(state={}), status=401)

    assert len(captured) == 1
    row = captured[0]
    assert row.workspace_id is None
    assert row.user_id is None
    assert row.payload["status_code"] == 401


async def test_failed_login_leaves_an_audit_row(captured, monkeypatch):
    """The event an auditor asks for first.

    A rejected login has no tenant by definition — the credentials did not
    resolve to one. That is exactly why the NOT NULL constraint made this
    unrecordable, and exactly why it had to go.
    """
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    scope = make_scope(method="POST", path="/api/auth/login", state={})
    await run_middleware(scope, status=401)

    assert len(captured) == 1
    row = captured[0]
    assert row.action == "http.post"
    assert row.resource == "/api/auth/login"
    assert row.workspace_id is None
    assert row.payload["status_code"] == 401
    assert row.payload["ip"] == "10.0.0.7"


async def test_model_permits_a_null_workspace(captured, monkeypatch):
    """Guards the constraint itself, not just the middleware's use of it."""
    assert AuditLog.__table__.columns["workspace_id"].nullable is True


async def test_disabled_flag_writes_nothing(captured, monkeypatch):
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", False)

    await run_middleware(
        make_scope(state={"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()})
    )

    assert captured == []


async def test_write_failure_does_not_escape(monkeypatch, caplog):
    """A database outage must warn, never take the request down with it."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    def _boom():
        raise RuntimeError("database is down")

    monkeypatch.setattr("app.database.async_session_factory", _boom, raising=False)

    await run_middleware(
        make_scope(state={"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()})
    )
    # Reaching here at all is the assertion: the exception stayed inside the
    # background task and the response completed.


async def test_health_probes_are_not_audited(captured, monkeypatch):
    """Liveness checks would otherwise bury the trail in noise.

    The container healthcheck hits /api/health every 10 seconds. Auditing it
    adds thousands of rows a day that mean nothing and make the rows that
    matter harder to find.
    """
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    for path in ("/api/health", "/api/metrics"):
        await run_middleware(make_scope(path=path, state={}))

    assert captured == []


async def test_exemption_does_not_extend_to_credential_endpoints(captured, monkeypatch):
    """Only probes are exempt. /api/auth/* is allowlisted but still audited."""
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    for path in ("/api/auth/login", "/api/auth/register", "/api/auth/refresh"):
        await run_middleware(make_scope(method="POST", path=path, state={}), status=401)

    assert len(captured) == 3
