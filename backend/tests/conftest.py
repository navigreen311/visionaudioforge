"""Shared test fixtures for the VisionAudioForge test suite."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.utils import (
    audio_to_wav_bytes,
    create_test_audio,
    create_test_image,
    create_test_user_data,
    image_to_png_bytes,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_app():
    """Provide an async HTTP client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# Keep legacy name for backward compatibility
@pytest.fixture
async def client(test_app):
    """Alias for test_app — backward-compatible fixture name."""
    yield test_app


@pytest.fixture
def test_image() -> bytes:
    """Create a solid gray test image as PNG bytes."""
    img = create_test_image()
    return image_to_png_bytes(img)


@pytest.fixture
def test_audio() -> bytes:
    """Create a 440 Hz sine wave as WAV bytes."""
    audio = create_test_audio()
    return audio_to_wav_bytes(audio)


@pytest.fixture
async def auth_headers(test_app) -> dict:
    """Register a test user, login, and return authorization headers.

    Since auth endpoints are currently stubs (501), this fixture returns
    a placeholder header. When auth is implemented, this will perform
    real registration and login flows.
    """
    user_data = create_test_user_data()

    # Attempt registration
    reg_resp = await test_app.post("/api/auth/register", json=user_data)

    # Attempt login
    login_resp = await test_app.post(
        "/api/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )

    # If auth is implemented, extract token; otherwise use test placeholder
    if login_resp.status_code == 200:
        token = login_resp.json().get("access_token", "test-token")
    else:
        token = "test-token-placeholder"

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_workspace_id() -> str:
    """Return a test workspace UUID.

    When workspace creation is implemented, this will use the API.
    """
    return "00000000-0000-0000-0000-000000000001"
