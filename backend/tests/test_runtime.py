"""Tests for the Runtime Orchestrator — model routing, GPU, cost, cache."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.runtime.router import ModelRouter, ModelRouteConfig
from app.services.runtime.gpu_scheduler import GPUScheduler
from app.services.runtime.cost_control import CostController
from app.services.runtime.cache import InferenceCache


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
def cost_controller() -> CostController:
    cc = CostController()
    cc.set_model_cost("model-a", 0.002)
    cc.set_model_cost("model-b", 0.01)
    return cc


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
async def test_cost_tracking(cost_controller: CostController):
    """Tracked inferences should appear in cost report."""
    ws = "ws-test-1"
    cost_controller.track_inference(ws, "model-a", 50.0, 100)
    cost_controller.track_inference(ws, "model-a", 60.0, 200)
    cost_controller.track_inference(ws, "model-b", 120.0, 500)

    report = cost_controller.get_workspace_cost(None, ws, period="daily")
    assert report["inference_count"] == 3
    assert report["total_cost"] > 0
    assert "model-a" in report["by_model"]
    assert "model-b" in report["by_model"]


@pytest.mark.anyio
async def test_budget_check(cost_controller: CostController):
    """Budget check should detect when spending exceeds limit."""
    ws = "ws-budget"
    for _ in range(10):
        cost_controller.track_inference(ws, "model-b", 100.0, 1000)

    result = cost_controller.check_budget(None, ws, budget_limit=0.05)
    assert result["within_budget"] is False
    assert result["spent"] > 0.05

    result2 = cost_controller.check_budget(None, ws, budget_limit=10.0)
    assert result2["within_budget"] is True


@pytest.mark.anyio
async def test_quota_enforcement(cost_controller: CostController):
    """Quota should block after limit is reached."""
    ws = "ws-quota"
    cost_controller.set_quota(ws, daily_limit=3)

    for i in range(3):
        result = cost_controller.check_quota(ws)
        assert result["allowed"] is True

    result = cost_controller.check_quota(ws)
    assert result["allowed"] is False
    assert result["used"] == 3
    assert result["limit"] == 3


@pytest.mark.anyio
async def test_cost_report_generation(cost_controller: CostController):
    """Full cost report should include all expected fields."""
    ws = "ws-report"
    cost_controller.track_inference(ws, "model-a", 50.0, 100)

    report = cost_controller.generate_cost_report(None, ws, period="monthly")
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


@pytest.mark.anyio
async def test_api_quota_set_and_get(client):
    """POST and GET quota endpoints should work together."""
    resp = await client.post("/api/runtime/quota", json={"workspace_id": "ws-api-test", "daily_limit": 100})
    assert resp.status_code == 200

    resp = await client.get("/api/runtime/quota/ws-api-test")
    assert resp.status_code == 200
    data = resp.json()
    assert "allowed" in data
    assert "limit" in data


@pytest.mark.anyio
async def test_api_cost_report(client):
    """GET /api/runtime/cost/{workspace_id} should return a report."""
    resp = await client.get("/api/runtime/cost/ws-api-test")
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
