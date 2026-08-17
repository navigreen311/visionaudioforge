"""Shared test fixtures for the VisionAudioForge test suite."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from tests.utils import (
    audio_to_wav_bytes,
    create_test_audio,
    create_test_image,
    create_test_user_data,
    image_to_png_bytes,
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "auth_enforced: run this test with the app-level auth middleware active "
        "(settings.AUTH_REQUIRED=True). Without it the suite runs open.",
    )
    config.addinivalue_line(
        "markers",
        "audit_enabled: run this test with request audit logging active "
        "(settings.AUDIT_ENABLED=True).",
    )


@pytest.fixture(autouse=True)
def _auth_enforcement(request):
    """Opt the suite *out* of app-level auth, deliberately and visibly.

    ``settings.AUTH_REQUIRED`` defaults to True in production so that a route
    added tomorrow is protected the moment it is registered. The existing test
    suite predates that boundary and calls endpoints anonymously, so tests run
    with it off unless they ask for it with ``@pytest.mark.auth_enforced``.

    The opt-out lives here, in one visible place, rather than being an accident
    of how each test happens to build its client.
    """
    previous = (settings.AUTH_REQUIRED, settings.AUDIT_ENABLED)
    settings.AUTH_REQUIRED = request.node.get_closest_marker("auth_enforced") is not None
    settings.AUDIT_ENABLED = request.node.get_closest_marker("audit_enabled") is not None
    try:
        yield
    finally:
        settings.AUTH_REQUIRED, settings.AUDIT_ENABLED = previous


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
