"""Notifications are per-user, persisted, and produced by real events.

The bell was served from a module-level list of five hardcoded entries returned
to every user of every workspace. Three properties failed at once and each is
pinned below:

  - it was the same five for everyone, in every tenant
  - marking one read mutated the shared list, so one person's click cleared the
    badge for all of them
  - a restart brought all five back unread, because nothing was stored

The last one cannot be tested here directly - the process does not restart
mid-suite - but it follows from the rows being in Postgres, which the read-back
tests establish.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.core.tenancy import unscoped
from app.database import async_session_factory
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.models.workspace import Workspace
from app.services.notifications.service import NotificationService

pytestmark = [pytest.mark.anyio, pytest.mark.auth_enforced]


@pytest.fixture
async def two_workspaces():
    """Two tenants, two users each. Enough to catch a leak in either direction."""
    made: dict[str, dict] = {}

    async with async_session_factory() as db:
        with unscoped():  # setup, not the query under test
            for label in ("alpha", "beta"):
                stamp = uuid.uuid4().hex[:8]
                workspace_id = uuid.uuid4()
                db.add(
                    Workspace(
                        id=workspace_id, name=f"{label}-{stamp}", slug=f"{label}-{stamp}"
                    )
                )
                await db.flush()

                users = []
                for index in range(2):
                    user = User(
                        id=uuid.uuid4(),
                        email=f"{label}-{index}-{stamp}@example.com",
                        hashed_password="x",
                        workspace_id=workspace_id,
                    )
                    db.add(user)
                    users.append(user.id)

                made[label] = {"workspace_id": workspace_id, "users": users}

            await db.commit()

    return made


@pytest.fixture
async def client():
    transport = ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _auth(user_id: uuid.UUID, workspace_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        {"sub": str(user_id), "workspace_id": str(workspace_id)}
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fan-out and isolation
# ---------------------------------------------------------------------------


async def test_emitting_notifies_every_user_in_that_workspace_only(two_workspaces):
    """One event, one row per recipient, and nothing for the other tenant."""
    alpha, beta = two_workspaces["alpha"], two_workspaces["beta"]

    async with async_session_factory() as db:
        with unscoped():
            written = await NotificationService.emit(
                db,
                alpha["workspace_id"],
                NotificationType.alert,
                title="Critical alert triggered",
                description="A rule fired",
                action_url="/alerts",
            )

    assert written == 2, "expected one row per user in the workspace"

    async with async_session_factory() as db:
        with unscoped():
            for user_id in alpha["users"]:
                assert await NotificationService.unread_count(db, user_id) == 1
            for user_id in beta["users"]:
                assert await NotificationService.unread_count(db, user_id) == 0, (
                    "a notification reached the other tenant"
                )


async def test_reading_is_per_user_not_shared(two_workspaces):
    """The defect that made the old bell wrong for everyone at once."""
    alpha = two_workspaces["alpha"]
    first, second = alpha["users"]

    async with async_session_factory() as db:
        with unscoped():
            await NotificationService.emit(
                db, alpha["workspace_id"], NotificationType.system, title="Something"
            )

            mine = await NotificationService.list_for_user(db, first)
            assert len(mine) == 1

            marked = await NotificationService.mark_read(
                db, first, uuid.UUID(mine[0]["id"])
            )
            assert marked is True

            assert await NotificationService.unread_count(db, first) == 0
            assert await NotificationService.unread_count(db, second) == 1, (
                "marking one user's notification read cleared another user's badge"
            )


async def test_a_notification_that_is_not_yours_cannot_be_marked_read(two_workspaces):
    """The id is not a capability.

    `mark_read` filters on user_id as well as id. Without that, anyone holding
    an id could clear someone else's badge - in any tenant.
    """
    alpha, beta = two_workspaces["alpha"], two_workspaces["beta"]

    async with async_session_factory() as db:
        with unscoped():
            await NotificationService.emit(
                db, alpha["workspace_id"], NotificationType.system, title="Alpha only"
            )
            theirs = await NotificationService.list_for_user(db, alpha["users"][0])
            assert theirs

            marked = await NotificationService.mark_read(
                db, beta["users"][0], uuid.UUID(theirs[0]["id"])
            )
            assert marked is False, "another tenant marked this notification read"

            assert await NotificationService.unread_count(db, alpha["users"][0]) == 1


async def test_mark_all_read_stops_at_this_user(two_workspaces):
    alpha = two_workspaces["alpha"]
    first, second = alpha["users"]

    async with async_session_factory() as db:
        with unscoped():
            for index in range(3):
                await NotificationService.emit(
                    db,
                    alpha["workspace_id"],
                    NotificationType.pipeline,
                    title=f"Run {index} completed",
                )

            assert await NotificationService.mark_all_read(db, first) == 3
            assert await NotificationService.unread_count(db, first) == 0
            assert await NotificationService.unread_count(db, second) == 3


async def test_a_workspace_with_no_users_is_not_an_error():
    """A system workspace has nobody to tell, which is not a failure."""
    async with async_session_factory() as db:
        with unscoped():
            assert (
                await NotificationService.emit(
                    db, uuid.uuid4(), NotificationType.system, title="Nobody home"
                )
                == 0
            )


# ---------------------------------------------------------------------------
# Through the API
# ---------------------------------------------------------------------------


async def test_the_bell_shows_this_users_notifications(client, two_workspaces):
    alpha = two_workspaces["alpha"]
    user_id = alpha["users"][0]

    async with async_session_factory() as db:
        with unscoped():
            await NotificationService.emit(
                db,
                alpha["workspace_id"],
                NotificationType.model,
                title="Model training complete",
                description="resnet50 finished",
                action_url="/train",
            )

    headers = _auth(user_id, alpha["workspace_id"])

    count = await client.get("/api/notifications/unread-count", headers=headers)
    assert count.status_code == 200, count.text
    assert count.json()["count"] == 1

    listing = await client.get("/api/notifications", headers=headers)
    assert listing.status_code == 200, listing.text
    items = listing.json()
    assert len(items) == 1

    # The shape the console's NotificationCenter reads.
    item = items[0]
    assert set(item) == {
        "id",
        "type",
        "title",
        "description",
        "read",
        "created_at",
        "action_url",
    }
    assert item["type"] == "model"
    assert item["read"] is False


async def test_marking_an_unknown_notification_read_is_a_404(client, two_workspaces):
    """It used to answer 200 with `{"success": false}`, which nothing checked."""
    alpha = two_workspaces["alpha"]
    headers = _auth(alpha["users"][0], alpha["workspace_id"])

    response = await client.patch(
        f"/api/notifications/{uuid.uuid4()}/read", headers=headers
    )
    assert response.status_code == 404, response.text


async def test_two_users_of_one_workspace_see_separate_badges(client, two_workspaces):
    """The same assertion as the service test, through the routes the bell calls."""
    alpha = two_workspaces["alpha"]
    first, second = alpha["users"]

    async with async_session_factory() as db:
        with unscoped():
            await NotificationService.emit(
                db, alpha["workspace_id"], NotificationType.alert, title="Fired"
            )

    first_headers = _auth(first, alpha["workspace_id"])
    second_headers = _auth(second, alpha["workspace_id"])

    listing = await client.get("/api/notifications", headers=first_headers)
    notification_id = listing.json()[0]["id"]

    marked = await client.patch(
        f"/api/notifications/{notification_id}/read", headers=first_headers
    )
    assert marked.status_code == 200, marked.text

    mine = await client.get("/api/notifications/unread-count", headers=first_headers)
    theirs = await client.get("/api/notifications/unread-count", headers=second_headers)

    assert mine.json()["count"] == 0
    assert theirs.json()["count"] == 1


# ---------------------------------------------------------------------------
# Producers
# ---------------------------------------------------------------------------


async def test_the_notifications_table_is_the_only_source():
    """No handler answers from a literal.

    tests/test_no_fabricated_api_data.py enforces this across every route
    module; this asserts it for the one that was the reason that guard needed an
    exception, so the exception's removal is pinned here too.
    """
    import pathlib

    source = (
        pathlib.Path(__file__).resolve().parent.parent
        / "app"
        / "api"
        / "routes"
        / "notifications.py"
    ).read_text(encoding="utf-8")

    assert "_notifications = [" not in source
    assert "NotificationService" in source
