"""Durability and scoping for account security state and settings.

Every store these routes used to rely on was a module-level list. That made the
data wrong in two ways rather than one — it vanished on restart, and it was not
scoped to anyone. These tests pin both properties down.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.security import LoginEvent, LoginStatus, UserSession, UserTwoFactor
from app.models.settings import AppearancePreference, WorkspaceIntegration
from app.models.user import User
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


async def _seed_user(session, email: str | None = None) -> User:
    """Insert a user to hang security state off."""
    user = User(
        id=uuid4(),
        email=email or f"user-{uuid4().hex[:8]}@example.com",
        hashed_password="not-a-real-hash",
    )
    session.add(user)
    await session.commit()
    return user


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sessions_survive_a_restart_and_stay_per_user():
    """Two users must not see each other's sessions, before or after a restart."""
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    try:
        async with factory() as session:
            alice = await _seed_user(session)
            bob = await _seed_user(session)
            session.add_all(
                [
                    UserSession(
                        user_id=alice.id, device="Alice Laptop", is_current=True
                    ),
                    UserSession(user_id=alice.id, device="Alice Phone"),
                    UserSession(user_id=bob.id, device="Bob Desktop"),
                ]
            )
            await session.commit()
            alice_id, bob_id = alice.id, bob.id
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            alice_rows = (
                await session.execute(
                    select(UserSession).where(UserSession.user_id == alice_id)
                )
            ).scalars().all()
            bob_rows = (
                await session.execute(
                    select(UserSession).where(UserSession.user_id == bob_id)
                )
            ).scalars().all()

        assert sorted(r.device for r in alice_rows) == ["Alice Laptop", "Alice Phone"]
        assert [r.device for r in bob_rows] == ["Bob Desktop"]
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_revoking_a_session_leaves_an_auditable_row():
    """Revocation marks the row rather than deleting it."""
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    try:
        async with factory() as session:
            user = await _seed_user(session)
            row = UserSession(user_id=user.id, device="Laptop")
            session.add(row)
            await session.commit()

            from datetime import datetime, timezone

            row.revoked_at = datetime.now(timezone.utc)
            await session.commit()
            row_id = row.id

        async with factory() as session:
            stored = (
                await session.execute(
                    select(UserSession).where(UserSession.id == row_id)
                )
            ).scalar_one()
            assert stored.revoked_at is not None
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Two-factor
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_two_factor_is_per_user_not_global():
    """The regression this table exists for.

    A module-level ``_2fa_enabled`` boolean meant one account enabling 2FA
    reported it as enabled for every other account too.
    """
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    try:
        async with factory() as session:
            enrolled = await _seed_user(session)
            other = await _seed_user(session)
            session.add(UserTwoFactor(user_id=enrolled.id, enabled=True))
            await session.commit()
            enrolled_id, other_id = enrolled.id, other.id
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            mine = (
                await session.execute(
                    select(UserTwoFactor).where(UserTwoFactor.user_id == enrolled_id)
                )
            ).scalar_one_or_none()
            theirs = (
                await session.execute(
                    select(UserTwoFactor).where(UserTwoFactor.user_id == other_id)
                )
            ).scalar_one_or_none()

        assert mine is not None and mine.enabled is True
        assert theirs is None, "the other user must not inherit an enrolment"
    finally:
        await restarted_engine.dispose()


# ---------------------------------------------------------------------------
# Login history
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_history_records_failures_and_survives_a_restart():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    try:
        async with factory() as session:
            user = await _seed_user(session)
            session.add_all(
                [
                    LoginEvent(user_id=user.id, status=LoginStatus.success),
                    LoginEvent(user_id=user.id, status=LoginStatus.failed),
                ]
            )
            await session.commit()
            user_id = user.id
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            rows = (
                await session.execute(
                    select(LoginEvent).where(LoginEvent.user_id == user_id)
                )
            ).scalars().all()

        # A history that drops failures cannot show an account being probed.
        assert {r.status for r in rows} == {LoginStatus.success, LoginStatus.failed}
    finally:
        await restarted_engine.dispose()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_appearance_preferences_survive_a_restart():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    saved = {"theme": "dark", "sidebarWidth": "wide", "language": "fr"}

    try:
        async with factory() as session:
            user = await _seed_user(session)
            session.add(
                AppearancePreference(user_id=user.id, preferences=saved)
            )
            await session.commit()
            user_id = user.id
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            row = (
                await session.execute(
                    select(AppearancePreference).where(
                        AppearancePreference.user_id == user_id
                    )
                )
            ).scalar_one()
        assert row.preferences["theme"] == "dark"
        assert row.preferences["sidebarWidth"] == "wide"
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_workspace_integrations_are_scoped_and_durable():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    try:
        async with factory() as session:
            ours = await seed_workspace(session, "integrations-ours")
            theirs = await seed_workspace(session, "integrations-theirs")
            session.add_all(
                [
                    WorkspaceIntegration(
                        workspace_id=ours, name="Slack", type="messaging", enabled=True
                    ),
                    WorkspaceIntegration(
                        workspace_id=theirs, name="PagerDuty", type="paging"
                    ),
                ]
            )
            await session.commit()
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            mine = (
                await session.execute(
                    select(WorkspaceIntegration).where(
                        WorkspaceIntegration.workspace_id == ours
                    )
                )
            ).scalars().all()

        assert [r.name for r in mine] == ["Slack"]
    finally:
        await restarted_engine.dispose()
