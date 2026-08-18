"""Tests for the Semantic Memory system — service, promotion rules, session bridge, and API."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
AGENT_ID = uuid.uuid4()


def _fake_memory(**overrides: Any) -> MagicMock:
    """Return a MagicMock that quacks like a SemanticMemory ORM instance."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "workspace_id": WORKSPACE_ID,
        "scope": "workspace",
        "category": "fact",
        "content": "The project uses Python 3.12",
        "embedding": None,
        "importance_score": 0.5,
        "freshness_score": 1.0,
        "access_count": 0,
        "last_accessed": None,
        "source": None,
        "source_type": "system",
        "confidence": 1.0,
        "expires_at": None,
        "is_private": False,
        "owner_id": None,
        "tags": ["python"],
        "related_memory_ids": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class FakeScalarResult:
    """Mimics SQLAlchemy scalar result for select queries."""

    def __init__(self, items: list[Any]):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items

    def scalar_one(self):
        return self._items[0]

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._items[0] if self._items else None

    def one(self):
        return self._items[0] if self._items else None


class FakeRowResult:
    """Mimics SQLAlchemy result with rows (for group-by queries)."""

    def __init__(self, rows: list):
        self._rows = rows

    def all(self):
        return self._rows

    def scalar(self):
        return self._rows[0] if self._rows else None

    def one(self):
        return self._rows[0] if self._rows else None


class FakeUpdateResult:
    """Mimics SQLAlchemy update/delete result."""

    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount


def _mock_db(execute_side_effects=None):
    """Create an AsyncMock database session."""
    db = AsyncMock()
    if execute_side_effects:
        db.execute = AsyncMock(side_effect=execute_side_effects)
    return db


# ---------------------------------------------------------------------------
# Test: Store and Recall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_and_recall():
    """Storing a memory and recalling it returns the memory."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    db = AsyncMock()
    db.flush = AsyncMock()

    # Store
    mem = await svc.store(
        db=db,
        workspace_id=WORKSPACE_ID,
        content="FastAPI is the web framework",
        category="fact",
        tags=["fastapi", "python"],
    )
    assert mem.content == "FastAPI is the web framework"
    assert mem.category == "fact"
    assert mem.importance_score == 0.5
    assert mem.freshness_score == 1.0
    assert mem.tags == ["fastapi", "python"]
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_store_with_ttl():
    """Store with ttl_days sets expires_at."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    db = AsyncMock()
    db.flush = AsyncMock()

    mem = await svc.store(
        db=db,
        workspace_id=WORKSPACE_ID,
        content="Temporary info",
        category="fact",
        ttl_days=7,
    )
    assert mem.expires_at is not None
    assert mem.expires_at > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Test: Recall respects scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_respects_scope():
    """Recall with scope filter only returns matching scope."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()

    ws_mem = _fake_memory(scope="workspace", content="workspace memory")
    agent_mem = _fake_memory(scope="agent", content="agent memory")

    # The query returns only workspace memories when scope=workspace
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult([ws_mem]),  # select query
            FakeUpdateResult(1),  # update access
        ]
    )

    result = await svc.recall(db=db, workspace_id=WORKSPACE_ID, query="memory", scope="workspace")
    assert len(result) == 1
    assert result[0].scope == "workspace"


# ---------------------------------------------------------------------------
# Test: Recall excludes private
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_excludes_private():
    """Recall without include_private excludes private memories."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()

    public_mem = _fake_memory(is_private=False, content="public info")

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult([public_mem]),
            FakeUpdateResult(1),
        ]
    )

    result = await svc.recall(db=db, workspace_id=WORKSPACE_ID, query="info", include_private=False)
    assert len(result) == 1
    assert result[0].is_private is False


# ---------------------------------------------------------------------------
# Test: Decay reduces freshness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_reduces_freshness():
    """decay_all multiplies freshness by decay_rate."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeUpdateResult(0),  # delete expired
            FakeUpdateResult(5),  # update decay
        ]
    )

    result = await svc.decay_all(db=db, workspace_id=WORKSPACE_ID, decay_rate=0.95)
    assert result["decayed"] == 5
    assert result["expired"] == 0


# ---------------------------------------------------------------------------
# Test: Decay deletes expired
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_deletes_expired():
    """decay_all removes memories with freshness < 0.01 or past expires_at."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeUpdateResult(3),  # delete expired
            FakeUpdateResult(2),  # update decay
        ]
    )

    result = await svc.decay_all(db=db, workspace_id=WORKSPACE_ID)
    assert result["expired"] == 3
    assert result["decayed"] == 2


# ---------------------------------------------------------------------------
# Test: Promote increases importance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_promote_increases_importance():
    """promote() increases importance_score by boost, capped at 1.0."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    mem = _fake_memory(importance_score=0.6)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([mem]))
    db.flush = AsyncMock()

    result = await svc.promote(db=db, memory_id=mem.id, boost=0.2)
    assert result.importance_score == 0.8


@pytest.mark.asyncio
async def test_promote_caps_at_one():
    """promote() caps importance at 1.0."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    mem = _fake_memory(importance_score=0.95)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([mem]))
    db.flush = AsyncMock()

    result = await svc.promote(db=db, memory_id=mem.id, boost=0.2)
    assert result.importance_score == 1.0


# ---------------------------------------------------------------------------
# Test: Demote decreases importance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demote_decreases():
    """demote() decreases importance_score, floored at 0.0."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    mem = _fake_memory(importance_score=0.3)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([mem]))
    db.flush = AsyncMock()

    result = await svc.demote(db=db, memory_id=mem.id, penalty=0.2)
    assert result.importance_score == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_demote_floors_at_zero():
    """demote() floors importance at 0.0."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    mem = _fake_memory(importance_score=0.1)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([mem]))
    db.flush = AsyncMock()

    result = await svc.demote(db=db, memory_id=mem.id, penalty=0.5)
    assert result.importance_score == 0.0


# ---------------------------------------------------------------------------
# Test: Conflict resolution keeps higher confidence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conflict_resolution_keeps_higher_confidence():
    """resolve_conflict keeps the memory with higher confidence."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    mem_a = _fake_memory(confidence=0.9, content="A is correct")
    mem_b = _fake_memory(confidence=0.4, content="B is wrong")

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult([mem_a]),
            FakeScalarResult([mem_b]),
        ]
    )
    db.flush = AsyncMock()

    winner = await svc.resolve_conflict(db=db, memory_id_a=mem_a.id, memory_id_b=mem_b.id)
    assert winner.confidence == 0.9
    assert "B is wrong" in winner.content  # merged
    assert mem_b.freshness_score == 0.0  # archived


# ---------------------------------------------------------------------------
# Test: Merge memories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_merge_memories():
    """merge_memories combines N memories into one with highest importance."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    m1 = _fake_memory(importance_score=0.8, confidence=0.9, tags=["a"], content="Fact 1")
    m2 = _fake_memory(importance_score=0.5, confidence=0.7, tags=["b"], content="Fact 2")

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([m1, m2]))
    db.flush = AsyncMock()

    merged = await svc.merge_memories(db=db, memory_ids=[m1.id, m2.id])
    assert merged.importance_score == 0.8
    assert merged.confidence == pytest.approx(0.8, abs=0.01)
    assert "Fact 1" in merged.content
    assert "Fact 2" in merged.content
    assert m1.freshness_score == 0.0  # archived
    assert m2.freshness_score == 0.0


# ---------------------------------------------------------------------------
# Test: Find related
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_related():
    """find_related returns memories with overlapping tags."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()
    source = _fake_memory(tags=["python", "web"])
    related = _fake_memory(tags=["python", "api"])

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult([source]),  # get source memory
            FakeScalarResult([related]),  # find related
        ]
    )

    result = await svc.find_related(db=db, memory_id=source.id)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Test: Privacy partition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_privacy_partition():
    """privacy_partition counts public vs private memories."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            FakeRowResult([5]),   # public count
            FakeRowResult([3]),   # private count
            FakeRowResult([(str(OWNER_ID), 3)]),  # by owner
        ]
    )

    result = await svc.privacy_partition(db=db, workspace_id=WORKSPACE_ID)
    assert result["public"] == 5
    assert result["private"] == 3


# ---------------------------------------------------------------------------
# Test: Promotion rules apply
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_promotion_rules_apply():
    """apply_rules promotes frequent-access and user-validated memories."""
    from app.services.memory.promotion_rules import MemoryPromotionEngine

    engine = MemoryPromotionEngine()

    frequent = _fake_memory(access_count=15, importance_score=0.5, source_type="system",
                            freshness_score=0.8, category="fact", confidence=1.0, tags=[])
    user_mem = _fake_memory(access_count=1, importance_score=0.5, source_type="user",
                            freshness_score=0.8, category="fact", confidence=1.0, tags=[])
    stale = _fake_memory(access_count=0, importance_score=0.2, source_type="system",
                         freshness_score=0.05, category="fact", confidence=1.0, tags=[])

    db = AsyncMock()
    # First call: all memories; second call: conflict check
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult([frequent, user_mem, stale]),  # for apply_rules
            FakeScalarResult([frequent, user_mem, stale]),  # for check_conflicts
        ]
    )
    db.flush = AsyncMock()

    result = await engine.apply_rules(db=db, workspace_id=WORKSPACE_ID)
    assert result["promotions"] >= 2  # frequent_access + user_validated
    assert result["archived"] >= 1  # stale


# ---------------------------------------------------------------------------
# Test: Session bridge continuity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_bridge_continuity():
    """SessionBridge stores and loads session context."""
    from app.services.memory.session_bridge import SessionBridge

    bridge = SessionBridge()

    # Test save
    db = AsyncMock()
    db.flush = AsyncMock()

    context = {"summary": "Discussed model training pipeline", "topics": ["ML", "pipeline"]}
    mem = await bridge.save_session_context(
        db=db, workspace_id=WORKSPACE_ID, agent_id=AGENT_ID, context=context
    )
    assert mem.category == "session_context"
    assert "agent_id" in mem.content


@pytest.mark.asyncio
async def test_session_bridge_load():
    """SessionBridge loads the most recent session context."""
    import json
    from app.services.memory.session_bridge import SessionBridge

    bridge = SessionBridge()

    stored_context = {"summary": "Worked on feature X"}
    stored_mem = _fake_memory(
        category="session_context",
        content=json.dumps({"agent_id": str(AGENT_ID), "context": stored_context}),
        tags=["session_bridge", f"agent:{AGENT_ID}"],
    )

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult([stored_mem]))

    result = await bridge.load_session_context(db=db, workspace_id=WORKSPACE_ID, agent_id=AGENT_ID)
    assert result == stored_context


@pytest.mark.asyncio
async def test_session_bridge_continuity_prompt():
    """build_continuity_prompt formats multiple session summaries."""
    import json
    from app.services.memory.session_bridge import SessionBridge

    bridge = SessionBridge()

    sessions = [
        _fake_memory(
            content=json.dumps({"agent_id": str(AGENT_ID), "context": {"summary": f"Session {i}"}}),
            created_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        for i in range(3)
    ]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeScalarResult(sessions))

    prompt = await bridge.build_continuity_prompt(db=db, workspace_id=WORKSPACE_ID, agent_id=AGENT_ID)
    assert "Previous sessions:" in prompt
    assert "Session" in prompt


# ---------------------------------------------------------------------------
# Test: Export / Import roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_import_roundtrip():
    """Export and import produce consistent data."""
    from app.services.memory.semantic_memory import SemanticMemoryService

    svc = SemanticMemoryService()

    mem1 = _fake_memory(content="Export test 1", category="fact", tags=["export"])
    mem2 = _fake_memory(content="Export test 2", category="event", tags=["export"])

    # Export
    db_export = AsyncMock()
    db_export.execute = AsyncMock(return_value=FakeScalarResult([mem1, mem2]))

    exported = await svc.export_memories(db=db_export, workspace_id=WORKSPACE_ID)
    assert len(exported) == 2
    assert exported[0]["content"] == "Export test 1"

    # Import
    db_import = AsyncMock()
    db_import.flush = AsyncMock()

    result = await svc.import_memories(db=db_import, workspace_id=WORKSPACE_ID, memories=exported)
    assert result["imported"] == 2


# ---------------------------------------------------------------------------
# Test: API endpoints (via FastAPI TestClient pattern)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_store_and_recall():
    """POST /semantic-memory/store persists a memory that /recall finds.

    This replaces two tests that patched `routes.semantic_memory.memory_service`
    and posted to `/api/memory/*`. Neither exists: the endpoints live under
    `/api/semantic-memory` and read and write the database directly, so the
    tests passed a mock to a module attribute that had been gone for some time.
    Driving the real endpoints against a real database is what actually
    establishes that storing a memory makes it recallable.
    """
    from httpx import ASGITransport, AsyncClient

    from app.database import get_async_session
    from app.main import app
    from tests.db_utils import (
        db_session_factory,
        fresh_engine,
        requires_postgres,
        seed_workspace,
    )

    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)
    async with factory() as session:
        workspace_id = await seed_workspace(session, "semantic-memory")

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    marker = f"gate-{uuid.uuid4().hex[:8]}"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            stored = await client.post(
                "/api/semantic-memory/store",
                json={
                    "content": f"The camera saw motion near {marker}",
                    "category": "security",
                    "importance": 0.7,
                    "workspace_id": str(workspace_id),
                },
            )
            assert stored.status_code == 201, stored.text
            assert marker in stored.json()["content"]

            recalled = await client.post(
                "/api/semantic-memory/recall",
                json={
                    "query": marker,
                    "category": "security",
                    "workspace_id": str(workspace_id),
                },
            )
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()

    assert recalled.status_code == 200, recalled.text
    body = recalled.json()
    assert body["total"] == 1
    assert marker in body["results"][0]["content"]
