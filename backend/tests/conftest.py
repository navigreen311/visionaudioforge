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


def _use_pool_free_engine() -> None:
    """Rebuild the application engine without a connection pool, for tests.

    asyncpg connections bind to the event loop that opened them, and the test
    suite creates a fresh loop per test — and, with the synchronous TestClient,
    per request. A pooled connection therefore outlives its loop and the next
    caller gets "attached to a different loop" or "Event loop is closed".
    NullPool opens and closes a connection per checkout, so nothing is ever
    reused across loops. Only worth doing in tests; production wants the pool.
    """
    try:
        import app.database as database
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool

        from app.config import settings

        database.engine = create_async_engine(
            settings.DATABASE_URL, poolclass=NullPool
        )
        database.async_session_factory = async_sessionmaker(
            database.engine, expire_on_commit=False
        )
    except Exception:
        pass


_use_pool_free_engine()


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


#: The workspace id DB-backed tests assume exists. Rows in most tables carry a
#: workspace foreign key, so this has to be a real row, not just a constant.
CANONICAL_TEST_WORKSPACE = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def test_workspace_id() -> str:
    """Return a test workspace UUID."""
    return CANONICAL_TEST_WORKSPACE


def _ensure_canonical_workspace_sync() -> None:
    """Ensure the canonical test workspace row exists.

    Endpoints that write workspace-scoped rows take their session from the app,
    not from the test helpers, so without this row every such request fails on
    a foreign key violation rather than exercising the endpoint.

    Done on a raw asyncpg connection in its own short-lived loop deliberately:
    the app's async engine binds its pool to whichever event loop first uses
    it, so seeding through it at import time would leave connections attached
    to a loop the tests never run in.
    """
    try:
        import asyncio

        import asyncpg

        from app.config import settings

        dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

        async def _seed() -> None:
            conn = await asyncpg.connect(dsn)
            try:
                await conn.execute(
                    "INSERT INTO workspaces (id, name, slug, created_at, updated_at) "
                    "VALUES ($1::uuid, $2, $3, now(), now()) "
                    "ON CONFLICT (id) DO NOTHING",
                    CANONICAL_TEST_WORKSPACE,
                    "test-workspace",
                    "test-workspace",
                )
            finally:
                await conn.close()

        asyncio.run(_seed())
    except Exception:
        # No database, or an unmigrated schema — DB-backed tests fail or skip
        # on their own terms rather than being masked here.
        pass


_ensure_canonical_workspace_sync()
