"""Tests for auth route wiring — verifies endpoints call through to AuthService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_fake_user(**overrides):
    """Build a mock User object with sensible defaults."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.email = overrides.get("email", "test@example.com")
    user.hashed_password = overrides.get("hashed_password", "hashed")
    user.role = overrides.get("role", "admin")
    user.workspace_id = overrides.get("workspace_id", uuid.uuid4())
    user.created_at = overrides.get("created_at", datetime.utcnow())
    user.updated_at = overrides.get("updated_at", datetime.utcnow())
    return user


def _mock_db_session():
    """Return an AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_register_endpoint_creates_user(client):
    """POST /api/auth/register should create a user and return tokens."""
    fake_user = _make_fake_user()
    register_result = {
        "access_token": "access-tok",
        "refresh_token": "refresh-tok",
        "user": fake_user,
    }

    with (
        patch("app.api.routes.auth.get_db") as mock_get_db,
        patch("app.api.routes.auth.AuthService") as MockAuthService,
    ):
        mock_db = _mock_db_session()
        mock_get_db.return_value = mock_db
        # Override the FastAPI dependency
        app.dependency_overrides[
            __import__("app.core.deps", fromlist=["get_db"]).get_db
        ] = lambda: mock_db

        mock_svc = AsyncMock()
        mock_svc.register = AsyncMock(return_value=register_result)
        MockAuthService.return_value = mock_svc

        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "new@example.com",
                "password": "securepass123",
                "workspace_name": "My Workspace",
            },
        )

        app.dependency_overrides.clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["access_token"] == "access-tok"
    assert data["refresh_token"] == "refresh-tok"
    assert data["user"]["email"] == fake_user.email


@pytest.mark.anyio
async def test_login_endpoint_returns_tokens(client):
    """POST /api/auth/login should authenticate and return tokens."""
    fake_user = _make_fake_user(email="login@example.com")
    login_result = {
        "access_token": "login-access",
        "refresh_token": "login-refresh",
        "user": fake_user,
    }

    with (
        patch("app.api.routes.auth.get_db") as mock_get_db,
        patch("app.api.routes.auth.AuthService") as MockAuthService,
    ):
        mock_db = _mock_db_session()
        app.dependency_overrides[
            __import__("app.core.deps", fromlist=["get_db"]).get_db
        ] = lambda: mock_db

        mock_svc = AsyncMock()
        mock_svc.login = AsyncMock(return_value=login_result)
        MockAuthService.return_value = mock_svc

        resp = await client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "securepass123"},
        )

        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "login-access"
    assert data["refresh_token"] == "login-refresh"
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.anyio
async def test_me_endpoint_returns_user(client):
    """GET /api/auth/me with valid token should return the user."""
    fake_user = _make_fake_user(email="me@example.com")

    # Create a real JWT so decode_token works
    token = create_access_token({"sub": str(fake_user.id)})

    # Mock DB to return our fake user when queried
    mock_db = _mock_db_session()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"


@pytest.mark.anyio
async def test_me_without_token_returns_401(client):
    """GET /api/auth/me without Authorization header should return 401/403."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)
