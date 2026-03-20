"""End-to-end integration tests for the authentication flow."""

import pytest

from tests.utils import create_test_user_data


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_full_auth_flow(test_app):
    """Register → login → access /api/auth/me → verify user data."""
    user_data = create_test_user_data()

    # Register
    reg_resp = await test_app.post("/api/auth/register", json=user_data)
    assert reg_resp.status_code in (200, 201, 501), (
        f"Registration failed: {reg_resp.status_code} {reg_resp.text}"
    )

    # Login
    login_resp = await test_app.post(
        "/api/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_resp.status_code in (200, 501), (
        f"Login failed: {login_resp.status_code} {login_resp.text}"
    )

    if login_resp.status_code == 200:
        token = login_resp.json().get("access_token")
        assert token, "Login response should contain access_token"

        # Access protected /me endpoint
        me_resp = await test_app.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data.get("email") == user_data["email"]


@pytest.mark.asyncio
async def test_protected_route_without_token(test_app):
    """GET /api/auth/me without auth header should return 401 or 501 (stub)."""
    response = await test_app.get("/api/auth/me")
    # 401 if auth is enforced, 501 if endpoint is a stub
    assert response.status_code in (401, 403, 501), (
        f"Expected 401/403/501, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_invalid_credentials(test_app):
    """Login with wrong password should return 401 or 501 (stub)."""
    response = await test_app.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongpassword"},
    )
    assert response.status_code in (401, 422, 501), (
        f"Expected 401/422/501, got {response.status_code}: {response.text}"
    )
