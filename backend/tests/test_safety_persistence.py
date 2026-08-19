"""Safety and compliance records survive a restart.

Scans, legal holds and voice consent are all records produced because someone
may ask for them later. Held in module-level dicts, "was this scanned?" and
"is this under hold?" silently became no on every deploy — and a legal hold
that evaporates lifts the block without anyone releasing it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.safety import LegalHold, SafetyScan, VoiceConsent
from app.services.safety.compliance import ComplianceManager
from app.services.safety.policy_engine import PolicyEngine
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def safety_env():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "safety")

    try:
        yield factory, str(workspace_id)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_legal_hold_survives_a_restart(safety_env):
    """Written through one engine, read back through a brand-new one."""
    factory, workspace_id = safety_env

    async with factory() as session:
        hold = await ComplianceManager.legal_hold(
            session,
            ["asset-1", "asset-2"],
            "pending litigation",
            "compliance-officer",
            workspace_id=workspace_id,
        )

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            active = await ComplianceManager.active_holds(
                session, workspace_id=workspace_id
            )
            assert [h["hold_id"] for h in active] == [hold["hold_id"]]
            assert active[0]["asset_ids"] == ["asset-1", "asset-2"]
            assert active[0]["user_id"] == "compliance-officer"
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_released_hold_records_who_and_when(safety_env):
    """Releasing is itself part of the record, not just a deletion."""
    factory, workspace_id = safety_env

    async with factory() as session:
        hold = await ComplianceManager.legal_hold(
            session, ["asset-1"], "reason", "admin", workspace_id=workspace_id
        )
        await ComplianceManager.release_hold(session, hold["hold_id"], "reviewer")

        stored = (
            await session.execute(
                select(LegalHold).where(LegalHold.id == uuid.UUID(hold["hold_id"]))
            )
        ).scalar_one()

        assert stored.released is True
        assert stored.released_by == "reviewer"
        assert stored.released_at is not None


@pytest.mark.anyio
async def test_holds_are_workspace_scoped(safety_env):
    """One tenant's holds are not reported to another."""
    factory, workspace_id = safety_env

    async with factory() as session:
        other = str(await seed_workspace(session, "safety-other"))
        await ComplianceManager.legal_hold(
            session, ["mine"], "r", "admin", workspace_id=workspace_id
        )
        await ComplianceManager.legal_hold(
            session, ["theirs"], "r", "admin", workspace_id=other
        )

        mine = await ComplianceManager.active_holds(session, workspace_id=workspace_id)
        assert [h["asset_ids"] for h in mine] == [["mine"]]


@pytest.mark.anyio
async def test_voice_consent_survives_a_restart(safety_env):
    """A granted consent must not read as "never asked" after a deploy."""
    factory, _ = safety_env
    owner = f"owner-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        await PolicyEngine.record_voice_consent(session, "user-1", owner)

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            granted = await PolicyEngine.check_voice_clone_consent(
                session, "user-1", owner
            )
            assert granted["consent"] is True

            ungranted = await PolicyEngine.check_voice_clone_consent(
                session, "user-2", owner
            )
            assert ungranted["consent"] is False
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_scan_is_recorded_and_readable_after_restart(safety_env):
    """A scan result is a compliance record, so it outlives the process."""
    factory, workspace_id = safety_env
    asset_id = f"asset-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        session.add(
            SafetyScan(
                id=uuid.uuid4(),
                workspace_id=uuid.UUID(workspace_id),
                asset_id=asset_id,
                scan_type="image",
                faces_detected=2,
                risk_score=0.45,
                result={
                    "faces_detected": 2,
                    "pii_found": [{"type": "face"}],
                    "risk_score": 0.45,
                },
            )
        )
        await session.commit()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            stored = (
                await session.execute(
                    select(SafetyScan).where(SafetyScan.asset_id == asset_id)
                )
            ).scalar_one()

            assert stored.faces_detected == 2
            assert stored.risk_score == pytest.approx(0.45)
            assert stored.result["pii_found"] == [{"type": "face"}]
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_export_check_reads_the_stored_scan(safety_env):
    """The check that always passed because the store was empty.

    check_export_allowed was handed a blank scan every time, so an asset with
    PII on record still exported cleanly.
    """
    factory, workspace_id = safety_env
    asset_id = f"asset-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        session.add(
            SafetyScan(
                id=uuid.uuid4(),
                workspace_id=uuid.UUID(workspace_id),
                asset_id=asset_id,
                scan_type="text",
                faces_detected=0,
                risk_score=0.3,
                result={
                    "faces_detected": 0,
                    "pii_found": [{"type": "ssn"}],
                    "risk_score": 0.3,
                },
            )
        )
        await session.commit()

        stored = (
            await session.execute(
                select(SafetyScan)
                .where(SafetyScan.asset_id == asset_id)
                .order_by(SafetyScan.created_at.desc())
                .limit(1)
            )
        ).scalar_one()

        verdict = PolicyEngine.check_export_allowed(stored.result, "strict_pii")
        assert verdict["allowed"] is False
