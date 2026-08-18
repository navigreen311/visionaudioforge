"""Tests for the Runtime Orchestrator — model routing, GPU, cost, cache."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.runtime.router import ModelRouter, ModelRouteConfig
from app.services.runtime.gpu_scheduler import GPUScheduler
from app.services.runtime.cost_control import CostController
from app.services.runtime.cache import InferenceCache
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def model_router() -> ModelRouter:
    r = ModelRouter()
    r.register_model("fast-small", ModelRouteConfig(
        model_id="fast-small", priority=1, max_latency_ms=100,
        cost_per_inference=0.001, warm=True,
    ))
    r.register_model("accurate-large", ModelRouteConfig(
        model_id="accurate-large", priority=5, max_latency_ms=5000,
        cost_per_inference=0.01, warm=False,
    ))
    r.register_model("mid-tier", ModelRouteConfig(
        model_id="mid-tier", priority=3, max_latency_ms=1000,
        cost_per_inference=0.005, warm=True,
    ))
    return r


@pytest.fixture
def gpu_scheduler() -> GPUScheduler:
    return GPUScheduler()


@pytest.fixture
async def cost_env():
    """A cost controller backed by a real database.

    Cost and quota state is now rows, not per-instance dicts, so these tests
    need a session and a real workspace to hang the rows off.
    """
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)

    cc = CostController()
    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "runtime-cost"))
        await cc.set_model_cost(session, "model-a", 0.002)
        await cc.set_model_cost(session, "model-b", 0.01)

    try:
        yield cc, factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
def inference_cache() -> InferenceCache:
    return InferenceCache()


# ---------------------------------------------------------------------------
# Model Router Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_model_routing_selects_cheapest(model_router: ModelRouter):
    """Route should pick the cheapest model when no latency constraint."""
    result = model_router.route("inference")
    assert result["model_id"] == "fast-small"
    assert "cheapest" in result["reason"]


@pytest.mark.anyio
async def test_model_routing_respects_latency(model_router: ModelRouter):
    """When latency constraint eliminates cheapest, next cheapest is chosen."""
    result = model_router.route("inference", constraints={"max_latency_ms": 5000})
    assert result["model_id"] == "fast-small"  # still cheapest and within budget


@pytest.mark.anyio
async def test_fallback_chain(model_router: ModelRouter):
    """Fallback chain should try models in order."""
    model_router.add_fallback_chain("fast-small", ["mid-tier", "accurate-large"])

    # Register executors: first fails, second succeeds
    model_router.register_executor("fast-small", lambda x: (_ for _ in ()).throw(RuntimeError("down")))
    model_router.register_executor("mid-tier", lambda x: {"output": "ok"})
    model_router.register_executor("accurate-large", lambda x: {"output": "backup"})

    result = await model_router.execute_with_fallback("fast-small", {"prompt": "test"})
    assert result["model_used"] == "mid-tier"
    assert result["fallback_used"] is True
    assert result["result"] == {"output": "ok"}


@pytest.mark.anyio
async def test_fallback_chain_all_fail(model_router: ModelRouter):
    """When all models fail, result should indicate failure."""
    model_router.add_fallback_chain("fast-small", ["mid-tier"])
    model_router.register_executor("fast-small", lambda x: (_ for _ in ()).throw(RuntimeError("fail")))
    model_router.register_executor("mid-tier", lambda x: (_ for _ in ()).throw(RuntimeError("fail")))

    result = await model_router.execute_with_fallback("fast-small", {"input": "x"})
    assert result["model_used"] == "none"
    assert "error" in result["result"]


# ---------------------------------------------------------------------------
# GPU Scheduler Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_gpu_status_returns_info(gpu_scheduler: GPUScheduler):
    """GPU status should return at least one device entry."""
    status = gpu_scheduler.get_gpu_status()
    assert isinstance(status, list)
    assert len(status) >= 1
    assert "device_id" in status[0]
    assert "name" in status[0]


@pytest.mark.anyio
async def test_memory_estimation(gpu_scheduler: GPUScheduler):
    """Memory estimation should scale with params and dtype."""
    # 1M params * 4 bytes = ~4MB for params, + 4MB activations (batch=1) = ~8MB
    est_f32 = gpu_scheduler.estimate_memory(1_000_000, batch_size=1, dtype="float32")
    est_f16 = gpu_scheduler.estimate_memory(1_000_000, batch_size=1, dtype="float16")
    assert est_f32["estimated_mb"] > est_f16["estimated_mb"]
    assert est_f32["estimated_mb"] == pytest.approx(7.63, rel=0.1)


@pytest.mark.anyio
async def test_memory_estimation_batch_size(gpu_scheduler: GPUScheduler):
    """Larger batch size should require more memory."""
    est1 = gpu_scheduler.estimate_memory(1_000_000, batch_size=1)
    est4 = gpu_scheduler.estimate_memory(1_000_000, batch_size=4)
    assert est4["estimated_mb"] > est1["estimated_mb"]


@pytest.mark.anyio
async def test_schedule_job_priority(gpu_scheduler: GPUScheduler):
    """High priority jobs should jump the queue."""
    gpu_scheduler.schedule_job("job-1", 1_000_000, priority="normal")
    gpu_scheduler.schedule_job("job-2", 1_000_000, priority="normal")
    result = gpu_scheduler.schedule_job("job-3", 1_000_000, priority="high")
    assert result["position_in_queue"] == 0


@pytest.mark.anyio
async def test_loading_strategy(gpu_scheduler: GPUScheduler):
    """Loading strategy should match access frequency thresholds."""
    hot = gpu_scheduler.model_loading_strategy(1_000_000, access_frequency=15)
    assert hot["strategy"] == "hot"

    warm = gpu_scheduler.model_loading_strategy(1_000_000, access_frequency=5)
    assert warm["strategy"] == "warm"

    cold = gpu_scheduler.model_loading_strategy(1_000_000, access_frequency=0.5)
    assert cold["strategy"] == "cold"


# ---------------------------------------------------------------------------
# Cost Control Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cost_tracking(cost_env):
    """Tracked inferences should appear in cost report."""
    cc, factory, ws = cost_env
    async with factory() as session:
        await cc.track_inference(session, ws, "model-a", 50.0, 100)
        await cc.track_inference(session, ws, "model-a", 60.0, 200)
        await cc.track_inference(session, ws, "model-b", 120.0, 500)

        report = await cc.get_workspace_cost(session, ws, period="daily")

    assert report["inference_count"] == 3
    assert report["total_cost"] > 0
    assert "model-a" in report["by_model"]
    assert "model-b" in report["by_model"]


@pytest.mark.anyio
async def test_budget_check(cost_env):
    """Budget check should detect when spending exceeds limit."""
    cc, factory, ws = cost_env
    async with factory() as session:
        for _ in range(10):
            await cc.track_inference(session, ws, "model-b", 100.0, 1000)

        result = await cc.check_budget(session, ws, budget_limit=0.05)
        assert result["within_budget"] is False
        assert result["spent"] > 0.05

        result2 = await cc.check_budget(session, ws, budget_limit=10.0)
        assert result2["within_budget"] is True


@pytest.mark.anyio
async def test_quota_enforcement(cost_env):
    """Quota should block after limit is reached."""
    cc, factory, ws = cost_env
    async with factory() as session:
        await cc.set_quota(session, ws, daily_limit=3)

        for _ in range(3):
            result = await cc.check_quota(session, ws)
            assert result["allowed"] is True

        result = await cc.check_quota(session, ws)

    assert result["allowed"] is False
    assert result["used"] == 3
    assert result["limit"] == 3


@pytest.mark.anyio
async def test_quota_survives_a_restart(cost_env):
    """A cap that resets on deploy is not a cap.

    Consume the allowance, then read through a brand-new engine: the workspace
    must still be blocked rather than starting over at zero used.
    """
    cc, factory, ws = cost_env
    async with factory() as session:
        await cc.set_quota(session, ws, daily_limit=2)
        await cc.check_quota(session, ws)
        await cc.check_quota(session, ws)

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            result = await cc.check_quota(session, ws)
        assert result["allowed"] is False, "quota reset itself across a restart"
        assert result["used"] == 2
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_spend_survives_a_restart(cost_env):
    """Cost reports must not read as 'nothing spent' after a deploy."""
    cc, factory, ws = cost_env
    async with factory() as session:
        await cc.track_inference(session, ws, "model-b", 10.0, 10)
        await cc.track_inference(session, ws, "model-b", 10.0, 10)

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            report = await cc.get_workspace_cost(session, ws, period="daily")
        assert report["inference_count"] == 2
        assert report["total_cost"] > 0
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_model_rates_survive_a_restart(cost_env):
    """Losing the rate table would silently re-price every model."""
    cc, factory, ws = cost_env

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            assert await cc._unit_cost(session, "model-b") == 0.01
            # An unpriced model still falls back to the documented default.
            assert await cc._unit_cost(session, "never-priced") == 0.001
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_cost_report_generation(cost_env):
    """Full cost report should include all expected fields."""
    cc, factory, ws = cost_env
    async with factory() as session:
        await cc.track_inference(session, ws, "model-a", 50.0, 100)
        report = await cc.generate_cost_report(session, ws, period="monthly")
    assert "period" in report
    assert "total_cost" in report
    assert "by_model" in report
    assert "by_day" in report
    assert "trend" in report
    assert "recommendations" in report


# ---------------------------------------------------------------------------
# Inference Cache Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cache_hit_miss(inference_cache: InferenceCache):
    """Cache should return None on miss and stored value on hit."""
    result = await inference_cache.get("model-x", {"prompt": "hello"})
    assert result is None

    await inference_cache.set("model-x", {"prompt": "hello"}, {"output": "world"})
    result = await inference_cache.get("model-x", {"prompt": "hello"})
    assert result == {"output": "world"}


@pytest.mark.anyio
async def test_cache_invalidation(inference_cache: InferenceCache):
    """Invalidation should clear cached entries."""
    await inference_cache.set("model-a", {"x": 1}, {"r": "a1"})
    await inference_cache.set("model-a", {"x": 2}, {"r": "a2"})
    await inference_cache.set("model-b", {"x": 1}, {"r": "b1"})

    count = await inference_cache.invalidate("model-a")
    assert count == 2

    # model-a entries gone
    assert await inference_cache.get("model-a", {"x": 1}) is None
    # model-b entries remain
    assert await inference_cache.get("model-b", {"x": 1}) == {"r": "b1"}


@pytest.mark.anyio
async def test_cache_invalidation_all(inference_cache: InferenceCache):
    """Invalidating without model_id clears everything."""
    await inference_cache.set("m1", {"a": 1}, {"r": 1})
    await inference_cache.set("m2", {"a": 2}, {"r": 2})

    count = await inference_cache.invalidate()
    assert count == 2


@pytest.mark.anyio
async def test_cache_stats(inference_cache: InferenceCache):
    """Stats should track hit/miss counts."""
    await inference_cache.get("m", {"a": 1})  # miss
    await inference_cache.set("m", {"a": 1}, {"r": 1})
    await inference_cache.get("m", {"a": 1})  # hit

    stats = await inference_cache.get_cache_stats()
    assert stats["hit_count"] == 1
    assert stats["miss_count"] == 1
    assert stats["hit_rate"] == 0.5
    assert stats["entries"] == 1


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_gpu_status(client):
    """GET /api/runtime/gpu should return device list."""
    resp = await client.get("/api/runtime/gpu")
    assert resp.status_code == 200
    data = resp.json()
    assert "devices" in data
    assert len(data["devices"]) >= 1


@pytest.mark.anyio
async def test_api_route(client):
    """POST /api/runtime/route should return a routing decision."""
    resp = await client.post("/api/runtime/route", json={"request_type": "inference"})
    assert resp.status_code == 200
    data = resp.json()
    assert "model_id" in data
    assert "reason" in data


@pytest.mark.anyio
async def test_api_cache_stats(client):
    """GET /api/runtime/cache/stats should return cache statistics."""
    resp = await client.get("/api/runtime/cache/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "hit_count" in data
    assert "miss_count" in data
    assert "hit_rate" in data


@pytest.fixture
async def db_client(cost_env):
    """HTTP client whose routes read the test database.

    Quota and cost are rows now, so the runtime endpoints need their session
    dependency pointed at the same database the fixtures seeded.
    """
    from app.database import get_async_session
    from app.main import app

    _cc, factory, workspace_id = cost_env

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, workspace_id
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.anyio
async def test_api_quota_set_and_get(db_client):
    """POST and GET quota endpoints should work together."""
    client, workspace_id = db_client
    resp = await client.post(
        "/api/runtime/quota",
        json={"workspace_id": workspace_id, "daily_limit": 100},
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/runtime/quota/{workspace_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 100
    assert data["allowed"] is True


@pytest.mark.anyio
async def test_api_cost_report(db_client):
    """GET /api/runtime/cost/{workspace_id} should return a report."""
    client, workspace_id = db_client
    resp = await client.get(f"/api/runtime/cost/{workspace_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cost" in data
    assert "by_model" in data


@pytest.mark.anyio
async def test_api_cache_clear(client):
    """POST /api/runtime/cache/clear should return cleared count."""
    resp = await client.post("/api/runtime/cache/clear")
    assert resp.status_code == 200
    data = resp.json()
    assert "cleared" in data


@pytest.mark.anyio
async def test_api_schedule(client):
    """GET /api/runtime/schedule should return job queue."""
    resp = await client.get("/api/runtime/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert "queue" in data
    assert "total_jobs" in data
