"""Tokens minted by AuthService carry the tenant they were issued for.

This is the other half of the tenancy plumbing. `test_auth_enforcement.py`
proves the middleware and `get_workspace_id` carry a `workspace_id` claim
correctly; these tests prove the tokens the product actually issues *have* one,
so tenant resolution costs no database round-trip.

Run:

    cd backend
    pytest tests/test_auth_workspace_claim.py -v
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import decode_token, hash_password
from app.main import app
from app.services.auth_service import (
    AuthService,
    access_token_claims,
    refresh_token_claims,
)

PASSWORD = "correct-horse-battery"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def fake_user(workspace_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "tenant@example.com"
    user.hashed_password = hash_password(PASSWORD)
    user.role = "admin"
    user.workspace_id = workspace_id
    return user


def db_returning(user) -> AsyncMock:
    """An AsyncSession mock whose next SELECT yields *user*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


# ---------------------------------------------------------------------------
# The claim builders
# ---------------------------------------------------------------------------


def test_access_token_claims_include_the_workspace():
    workspace_id = uuid.uuid4()
    claims = access_token_claims(fake_user(workspace_id))

    assert claims["workspace_id"] == str(workspace_id)


def test_access_token_claims_omit_a_missing_workspace():
    """Omitted, not null — a "None" string would reach a UUID parser."""
    claims = access_token_claims(fake_user(None))

    assert "workspace_id" not in claims
    assert claims["sub"]


def test_refresh_token_claims_are_identity_only():
    """A 7-day token must not pin a tenant that can change tomorrow."""
    claims = refresh_token_claims(fake_user(uuid.uuid4()))

    assert set(claims) == {"sub"}


# ---------------------------------------------------------------------------
# The tokens the service actually issues
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_mints_a_workspace_scoped_access_token():
    workspace_id = uuid.uuid4()
    user = fake_user(workspace_id)

    result = await AuthService(db_returning(user)).login(user.email, PASSWORD)

    assert decode_token(result["access_token"])["workspace_id"] == str(workspace_id)
    assert "workspace_id" not in decode_token(result["refresh_token"])


@pytest.mark.anyio
async def test_refresh_re_reads_the_workspace_from_the_user_row():
    """Reassignment lands on the next refresh, not seven days later."""
    from app.core.security import create_refresh_token

    old_workspace = uuid.uuid4()
    new_workspace = uuid.uuid4()

    user = fake_user(old_workspace)
    stale_refresh = create_refresh_token({"sub": str(user.id)})

    # The user has since been moved to a different workspace.
    user.workspace_id = new_workspace
    result = await AuthService(db_returning(user)).refresh(stale_refresh)

    assert decode_token(result["access_token"])["workspace_id"] == str(new_workspace)


@pytest.mark.anyio
async def test_register_mints_a_workspace_scoped_access_token():
    """The workspace is created during registration, so the claim must
    reflect the row as it stands *after* the flush that assigns its id."""
    added: list = []

    session = AsyncMock()
    session.add = MagicMock(side_effect=added.append)

    async def _flush() -> None:
        # Stand in for the database assigning server-side defaults.
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    session.flush = AsyncMock(side_effect=_flush)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # get_user_by_email must report "no such user" for registration to proceed.
    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=empty)

    result = await AuthService(session).register(
        email="new@example.com", password=PASSWORD, workspace_name="Acme"
    )

    claims = decode_token(result["access_token"])
    workspace = next(o for o in added if o.__class__.__name__ == "Workspace")
    assert claims["workspace_id"] == str(workspace.id)


# ---------------------------------------------------------------------------
# End to end: the issued token resolves without touching the database
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.auth_enforced
async def test_issued_token_resolves_its_workspace_with_no_db_lookup():
    """A login token, replayed against the app, lands on the right tenant.

    The probe depends on ``get_workspace_id`` and no database is configured
    here, so a passing assertion proves the value came from the signed claim
    rather than a users-table fallback.
    """
    from uuid import UUID

    from fastapi import Depends

    from app.core.deps import get_workspace_id

    workspace_id = uuid.uuid4()
    user = fake_user(workspace_id)
    tokens = await AuthService(db_returning(user)).login(user.email, PASSWORD)

    path = "/__ws_a_test__/claim_probe"

    async def _echo(resolved: UUID = Depends(get_workspace_id)):
        return {"workspace_id": str(resolved)}

    app.add_api_route(path, _echo, methods=["GET"])
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                path,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != path
        ]

    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(workspace_id)
