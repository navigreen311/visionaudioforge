"""Tests for workspace management service and routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.workspace_service import _slugify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(name="Test WS", slug="test-ws", owner_id=None, plan="free"):
    ws = MagicMock()
    ws.id = uuid.uuid4()
    ws.name = name
    ws.slug = slug
    ws.owner_id = owner_id or uuid.uuid4()
    ws.plan = plan
    ws.settings = {}
    ws.created_at = "2025-01-01T00:00:00Z"
    ws.updated_at = "2025-01-01T00:00:00Z"
    return ws


def _make_user(email="user@test.com", role="viewer", workspace_id=None):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.role = role
    user.workspace_id = workspace_id
    return user


def _mock_db():
    """Create an AsyncMock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


def _mock_scalar_result(value):
    """Create a mock result whose scalar_one_or_none and scalar_one return value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value
    return result


def _mock_scalars_result(values):
    """Create a mock result whose scalars().all() returns a list."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars_mock
    return result


# ---------------------------------------------------------------------------
# Unit: slug generation
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert _slugify("My Workspace") == "my-workspace"


def test_slugify_special_chars():
    assert _slugify("Hello World! @#$") == "hello-world"


def test_slugify_leading_trailing():
    assert _slugify("  --foo bar-- ") == "foo-bar"


# ---------------------------------------------------------------------------
# test_create_workspace_generates_slug
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_workspace_generates_slug():
    """create_workspace should auto-generate a slug from the name."""
    db = _mock_db()
    # slug uniqueness check returns None (no collision)
    db.execute.return_value = _mock_scalar_result(None)

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    result = await svc.create_workspace(
        name="My Cool Project",
        owner_id=uuid.uuid4(),
    )

    # The service should have called db.add with a Workspace instance
    db.add.assert_called_once()
    added_obj = db.add.call_args[0][0]
    assert added_obj.slug == "my-cool-project"
    assert added_obj.name == "My Cool Project"


# ---------------------------------------------------------------------------
# test_slug_uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_slug_uniqueness():
    """When a slug collides, create_workspace appends a numeric suffix."""
    db = _mock_db()

    existing_ws = _make_workspace(slug="test-ws")
    # First call: slug "test-ws" exists; second call: "test-ws-1" is free
    db.execute.side_effect = [
        _mock_scalar_result(existing_ws),  # "test-ws" taken
        _mock_scalar_result(None),          # "test-ws-1" available
    ]

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    result = await svc.create_workspace(name="Test WS", owner_id=uuid.uuid4())

    added_obj = db.add.call_args[0][0]
    assert added_obj.slug == "test-ws-1"


# ---------------------------------------------------------------------------
# test_get_workspace_stats
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_workspace_stats():
    """get_workspace_stats returns counts for all resource types."""
    db = _mock_db()
    ws = _make_workspace()

    # get_workspace_stats calls get_workspace (1 execute), then 5 count queries
    db.execute.side_effect = [
        _mock_scalar_result(ws),   # workspace lookup
        _mock_scalar_result(3),    # members count
        _mock_scalar_result(5),    # models count
        _mock_scalar_result(10),   # datasets count
        _mock_scalar_result(7),    # assets count
        _mock_scalar_result(2),    # pipelines count
    ]

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    stats = await svc.get_workspace_stats(ws.id)

    assert stats == {
        "members": 3,
        "models": 5,
        "datasets": 10,
        "assets": 7,
        "pipelines": 2,
    }


# ---------------------------------------------------------------------------
# test_invite_member
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_invite_member_creates_new_user():
    """invite_member creates a new user when the email doesn't exist."""
    db = _mock_db()
    ws = _make_workspace()
    ws_id = ws.id

    # 1) get_workspace succeeds, 2) user lookup returns None (new user)
    db.execute.side_effect = [
        _mock_scalar_result(ws),    # workspace exists
        _mock_scalar_result(None),  # user not found — will create
    ]

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    result = await svc.invite_member(ws_id, "new@test.com", role="analyst")

    db.add.assert_called_once()
    added_user = db.add.call_args[0][0]
    assert added_user.email == "new@test.com"
    assert added_user.role == "analyst"
    assert added_user.workspace_id == ws_id


@pytest.mark.anyio
async def test_invite_member_already_in_workspace():
    """invite_member raises 409 if user is already in the workspace."""
    db = _mock_db()
    ws = _make_workspace()
    existing_user = _make_user(email="existing@test.com", workspace_id=ws.id)

    db.execute.side_effect = [
        _mock_scalar_result(ws),            # workspace exists
        _mock_scalar_result(existing_user),  # user already a member
    ]

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.invite_member(ws.id, "existing@test.com")

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# test_update_member_role
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_member_role():
    """update_member_role changes a user's role."""
    db = _mock_db()
    ws_id = uuid.uuid4()
    user = _make_user(email="member@test.com", role="viewer", workspace_id=ws_id)

    db.execute.return_value = _mock_scalar_result(user)

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    result = await svc.update_member_role(ws_id, user.id, "analyst")

    assert user.role == "analyst"


@pytest.mark.anyio
async def test_update_member_role_invalid():
    """update_member_role raises 422 for invalid role names."""
    db = _mock_db()
    ws_id = uuid.uuid4()
    user = _make_user(workspace_id=ws_id)

    db.execute.return_value = _mock_scalar_result(user)

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_member_role(ws_id, user.id, "superuser")

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# test_remove_member
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_remove_member():
    """remove_member sets workspace_id to None."""
    db = _mock_db()
    ws_id = uuid.uuid4()
    user = _make_user(workspace_id=ws_id)

    db.execute.return_value = _mock_scalar_result(user)

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)
    await svc.remove_member(ws_id, user.id)

    assert user.workspace_id is None


@pytest.mark.anyio
async def test_remove_member_not_found():
    """remove_member raises 404 if user is not in the workspace."""
    db = _mock_db()
    ws_id = uuid.uuid4()

    db.execute.return_value = _mock_scalar_result(None)

    from app.services.workspace_service import WorkspaceService

    svc = WorkspaceService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.remove_member(ws_id, uuid.uuid4())

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# test_admin_only_endpoints (route-level authorization)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_only_endpoints(test_app, auth_headers):
    """Admin-only endpoints reject non-admin tokens with 401/403.

    Since auth stubs return 501 and auth_headers uses a placeholder,
    these endpoints should reject the request (not return 501 stubs).
    """
    ws_id = "00000000-0000-0000-0000-000000000001"

    # PUT workspace (admin only)
    resp = await test_app.put(
        f"/api/workspaces/{ws_id}",
        json={"name": "Updated"},
        headers=auth_headers,
    )
    assert resp.status_code in (401, 403)

    # POST invite member (admin only)
    resp = await test_app.post(
        f"/api/workspaces/{ws_id}/members",
        json={"email": "new@test.com", "role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code in (401, 403)

    # PUT change role (admin only)
    user_id = "00000000-0000-0000-0000-000000000002"
    resp = await test_app.put(
        f"/api/workspaces/{ws_id}/members/{user_id}",
        json={"role": "analyst"},
        headers=auth_headers,
    )
    assert resp.status_code in (401, 403)

    # DELETE remove member (admin only)
    resp = await test_app.delete(
        f"/api/workspaces/{ws_id}/members/{user_id}",
        headers=auth_headers,
    )
    assert resp.status_code in (401, 403)
