"""Tests for JWT authentication, RBAC, and auth routes."""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Unit tests — password hashing
# ---------------------------------------------------------------------------


def test_hash_and_verify_password():
    """hash_password produces a bcrypt hash; verify_password validates it."""
    plain = "securepassword123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongpassword!", hashed) is False


def test_stored_hash_format_is_bcrypt_cost_12():
    """Pin the on-disk format. Changing it silently orphans the users table."""
    assert hash_password("securepassword123").startswith("$2b$12$")


def test_legacy_hash_still_verifies():
    """A hash written by the previous passlib-based implementation must
    keep working. passlib's bcrypt backend emitted standard $2b$ hashes, so
    this cost-12 hash of "legacy-password" is byte-identical to what is
    already stored for existing users.

    If this fails, everyone who registered before the passlib removal is
    locked out.
    """
    legacy = "$2b$12$lwkfJJoHg0tdl2CyGy5iF.2cTs8E5ZZhyoxKy5OkYiOklCh2mN/6a"

    assert verify_password("legacy-password", legacy) is True
    assert verify_password("not-it", legacy) is False


def test_verify_password_returns_false_on_a_malformed_hash():
    """A corrupt record is a failed login, not a 500."""
    assert verify_password("anything", "not-a-bcrypt-hash") is False
    assert verify_password("anything", "") is False


def test_overlong_password_hashes_instead_of_raising():
    """bcrypt reads 72 bytes; passlib used to raise on anything longer."""
    long_password = "a" * 200
    hashed = hash_password(long_password)

    assert verify_password(long_password, hashed) is True
    # Truncation is the algorithm's behaviour, made explicit rather than hidden:
    # the first 72 bytes are what was actually hashed.
    assert verify_password("a" * 72, hashed) is True


# ---------------------------------------------------------------------------
# Unit tests — JWT tokens
# ---------------------------------------------------------------------------


def test_create_and_decode_token():
    """create_access_token round-trips through decode_token."""
    user_id = str(uuid.uuid4())
    token = create_access_token({"sub": user_id})

    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_refresh_token_has_correct_type():
    """create_refresh_token sets type='refresh' in the payload."""
    token = create_refresh_token({"sub": str(uuid.uuid4())})
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_token_rejects_garbage():
    """decode_token raises HTTPException 401 on invalid input."""
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-valid-jwt")
    assert exc_info.value.status_code == 401


def test_expired_token_is_rejected():
    """A token with a negative expiry should be rejected."""
    token = create_access_token(
        {"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration-style tests — auth routes (mocked DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    """Return a mock User object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.hashed_password = hash_password("password1234")
    user.role = "admin"
    user.workspace_id = uuid.uuid4()
    user.created_at = "2026-01-01T00:00:00Z"
    return user


@pytest.mark.anyio
async def test_register_creates_user_and_workspace(client):
    """POST /api/auth/register should create user+workspace and return tokens."""
    with patch("app.api.routes.auth.AuthService") as MockSvc:
        mock_svc = AsyncMock()
        MockSvc.return_value = mock_svc
        user_id = uuid.uuid4()
        ws_id = uuid.uuid4()
        mock_user_obj = MagicMock()
        mock_user_obj.id = user_id
        mock_user_obj.email = "new@example.com"
        mock_user_obj.role = "admin"
        mock_user_obj.workspace_id = ws_id
        mock_user_obj.created_at = "2026-01-01T00:00:00Z"

        mock_svc.register.return_value = {
            "access_token": "acc_tok",
            "refresh_token": "ref_tok",
            "user": mock_user_obj,
        }

        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "new@example.com",
                "password": "password1234",
                "workspace_name": "My Workspace",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@example.com"


@pytest.mark.anyio
async def test_login_returns_tokens(client):
    """POST /api/auth/login returns access and refresh tokens."""
    with patch("app.api.routes.auth.AuthService") as MockSvc:
        mock_svc = AsyncMock()
        MockSvc.return_value = mock_svc
        user_id = uuid.uuid4()
        ws_id = uuid.uuid4()
        mock_user_obj = MagicMock()
        mock_user_obj.id = user_id
        mock_user_obj.email = "login@example.com"
        mock_user_obj.role = "viewer"
        mock_user_obj.workspace_id = ws_id
        mock_user_obj.created_at = "2026-01-01T00:00:00Z"

        mock_svc.login.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
            "user": mock_user_obj,
        }

        resp = await client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "password1234"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "acc"
        assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_invalid_login_returns_401(client):
    """POST /api/auth/login with bad creds should raise 401 via service."""
    with patch("app.api.routes.auth.AuthService") as MockSvc:
        mock_svc = AsyncMock()
        MockSvc.return_value = mock_svc
        mock_svc.login.side_effect = HTTPException(
            status_code=401, detail="Invalid email or password"
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "bad@example.com", "password": "wrongpass123"},
        )
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_requires_auth(client):
    """GET /api/auth/me without a token returns 401.

    Previously asserted 403. ``HTTPBearer`` is configured with
    ``auto_error=False``, so the rejection comes from ``get_current_user`` (and,
    with ``AUTH_REQUIRED`` on, from the auth middleware before that) — both of
    which correctly answer 401 "who are you?" rather than 403 "not allowed".
    """
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_role_check_blocks_unauthorized():
    """require_role should raise 403 when the user lacks the needed role."""
    from app.core.deps import require_role

    checker = require_role("admin")

    mock_user = MagicMock()
    mock_user.role = "viewer"

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=mock_user)
    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail
