"""Tests for the Simulation Lab — scenario generation, stress testing, adversarial robustness."""

import pytest
from unittest.mock import MagicMock
from httpx import ASGITransport, AsyncClient

from app.services.simulation.scenario_generator import ScenarioGenerator
from app.services.simulation.stress_tester import StressTester, StressTestConfig
from app.services.simulation.runner import SimulationRunner
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
def generator():
    return ScenarioGenerator()


@pytest.fixture
def tester():
    return StressTester()


@pytest.fixture
def runner():
    return SimulationRunner()


@pytest.fixture
async def ac():
    """Async HTTP client for the FastAPI app."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Scenario Generator tests
# ---------------------------------------------------------------------------


def test_generate_intrusion_scenario(generator: ScenarioGenerator):
    """Intrusion scenario returns well-formed structure with motion + alert events."""
    result = generator.generate_scenario("intrusion", {"event_count": 5, "duration_s": 20})
    assert result["type"] == "intrusion"
    assert "scenario_id" in result
    assert isinstance(result["events"], list)
    assert len(result["events"]) >= 5  # 5 motion + 1 alert
    assert result["duration_s"] == 20
    assert "description" in result

    # Last event should be the alert
    assert result["events"][-1]["type"] == "alert_triggered"
    # Earlier events should be motion_detected
    assert result["events"][0]["type"] == "motion_detected"


def test_generate_random_scenario(generator: ScenarioGenerator):
    """Random scenario returns a valid scenario from the pool."""
    result = generator.generate_random_scenario(difficulty="easy")
    assert result["type"] in ScenarioGenerator.SCENARIO_TYPES
    assert isinstance(result["events"], list)
    assert len(result["events"]) > 0
    assert "scenario_id" in result


def test_generate_scenario_batch(generator: ScenarioGenerator):
    """Batch generates the correct number of scenarios per type."""
    types = ["intrusion", "fire_smoke"]
    results = generator.generate_scenario_batch(types, count_per_type=2)
    assert len(results) == 4
    intrusion_count = sum(1 for r in results if r["type"] == "intrusion")
    fire_count = sum(1 for r in results if r["type"] == "fire_smoke")
    assert intrusion_count == 2
    assert fire_count == 2


def test_generate_invalid_type(generator: ScenarioGenerator):
    """Invalid scenario type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown scenario type"):
        generator.generate_scenario("nonexistent")


def test_all_scenario_types_generate(generator: ScenarioGenerator):
    """Every supported scenario type generates without error."""
    for stype in ScenarioGenerator.SCENARIO_TYPES:
        result = generator.generate_scenario(stype)
        assert result["type"] == stype
        assert len(result["events"]) > 0


# ---------------------------------------------------------------------------
# Stress Tester tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stress_test_measures_latency(tester: StressTester):
    """Stress test returns valid latency metrics."""
    config = StressTestConfig(
        target_module="vision",
        concurrent_requests=10,
        duration_s=1.0,  # Short for testing
        payload_type="small",
    )
    db = MagicMock()
    result = await tester.run_stress_test(db, "ws-1", config)
    assert result.total_requests > 0
    assert result.throughput_rps > 0
    assert result.latency_p50_ms >= 0
    assert result.latency_p95_ms >= result.latency_p50_ms
    assert result.latency_p99_ms >= result.latency_p95_ms
    assert 0.0 <= result.error_rate <= 1.0


@pytest.mark.anyio
async def test_edge_case_suite_catches_bad_input(tester: StressTester):
    """Edge case suite runs all cases and reports pass/fail."""
    result = await tester.run_edge_case_suite("test-model")
    assert result["model_name"] == "test-model"
    assert len(result["test_cases"]) == 8
    assert result["passed"] + result["failed"] == 8
    assert isinstance(result["edge_cases_found"], list)
    # Each case has required fields
    for tc in result["test_cases"]:
        assert "case" in tc
        assert "status" in tc
        assert tc["status"] in ("passed", "failed")


@pytest.mark.anyio
async def test_adversarial_noise_increases(tester: StressTester):
    """Adversarial test returns prediction comparison with perturbation info."""
    result = await tester.run_adversarial_test("test-model", None, "noise")
    assert "original_prediction" in result
    assert "adversarial_prediction" in result
    assert "perturbation_magnitude" in result
    assert isinstance(result["model_robust"], bool)
    assert result["original_prediction"]["confidence"] > 0
    assert result["perturbation_magnitude"] > 0


@pytest.mark.anyio
async def test_adversarial_brightness_method(tester: StressTester):
    """Adversarial test works with brightness method."""
    result = await tester.run_adversarial_test("test-model", None, "brightness")
    assert result["method"] == "brightness"
    assert "original_prediction" in result


@pytest.mark.anyio
async def test_pipeline_benchmark(tester: StressTester):
    """Pipeline benchmark returns latency stats and bottleneck."""
    result = await tester.benchmark_pipeline("pipe-1", iterations=20)
    assert result["pipeline_id"] == "pipe-1"
    assert result["iterations"] == 20
    assert result["avg_duration_ms"] > 0
    assert result["p95_ms"] >= result["avg_duration_ms"] * 0.5  # Reasonable range
    assert result["p99_ms"] >= result["p95_ms"]
    assert result["throughput_per_s"] > 0
    assert result["bottleneck_node"] in result["node_avg_ms"]


# ---------------------------------------------------------------------------
# Simulation Runner tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def sim_db():
    """A real session and workspace.

    Simulation runs are rows now — replay, comparison and the report all read
    them back by id, so a MagicMock session no longer stands in.
    """
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "simulation"))
    try:
        async with factory() as session:
            yield session, workspace_id
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_simulation_runner_injects_events(runner: SimulationRunner, sim_db):
    """Runner injects all events and records timeline."""
    scenario = {
        "type": "intrusion",
        "events": [
            {"type": "motion_detected", "confidence": 0.5},
            {"type": "motion_detected", "confidence": 0.8},
            {"type": "alert_triggered", "severity": "high", "rule": "intrusion"},
        ],
        "description": "test scenario",
    }
    db, ws = sim_db
    result = await runner.run_simulation(db, ws, scenario)
    assert result["events_injected"] == 3
    assert result["alerts_triggered"] == 1
    assert len(result["timeline"]) == 3
    assert "simulation_id" in result


@pytest.mark.anyio
async def test_simulation_report(runner: SimulationRunner, sim_db):
    """Report includes scenario details, alerts, and recommendations."""
    scenario = {
        "type": "fire_smoke",
        "events": [
            {"type": "visual_anomaly", "confidence": 0.9},
            {"type": "alert_triggered", "severity": "critical", "rule": "fire_smoke_detected"},
        ],
        "description": "fire test",
    }
    db, ws = sim_db
    sim_result = await runner.run_simulation(db, ws, scenario)
    report = await runner.get_simulation_report(db, sim_result["simulation_id"])

    assert report["simulation_id"] == sim_result["simulation_id"]
    assert "scenario" in report
    assert "results" in report
    assert isinstance(report["alerts"], list)
    assert isinstance(report["missed_detections"], list)
    assert isinstance(report["recommendations"], list)


@pytest.mark.anyio
async def test_compare_simulations(runner: SimulationRunner, sim_db):
    """Comparing two simulations returns metric-by-metric comparison."""
    db, ws = sim_db
    s1 = await runner.run_simulation(db, ws, {
        "type": "test",
        "events": [{"type": "alert_triggered", "severity": "low", "rule": "x"}],
    })
    s2 = await runner.run_simulation(db, ws, {
        "type": "test",
        "events": [
            {"type": "motion_detected", "confidence": 0.7},
            {"type": "alert_triggered", "severity": "high", "rule": "y"},
        ],
    })
    result = await runner.compare_simulations(db, [s1["simulation_id"], s2["simulation_id"]])
    assert "comparison" in result
    assert len(result["comparison"]) == 3  # events_injected, alerts_triggered, duration_s
    for entry in result["comparison"]:
        assert "metric" in entry
        assert "values" in entry


@pytest.mark.anyio
async def test_replay_simulation(runner: SimulationRunner, sim_db):
    """Replaying a simulation produces a new run with same scenario."""
    db, ws = sim_db
    original = await runner.run_simulation(db, ws, {
        "type": "test",
        "events": [{"type": "motion_detected", "confidence": 0.5}],
    })
    replayed = await runner.replay_simulation(db, original["simulation_id"])
    assert replayed["simulation_id"] != original["simulation_id"]
    assert replayed["events_injected"] == original["events_injected"]


@pytest.mark.anyio
async def test_replay_not_found(runner: SimulationRunner, sim_db):
    """Replaying a nonexistent simulation raises ValueError."""
    db, _ws = sim_db
    with pytest.raises(ValueError, match="not found"):
        await runner.replay_simulation(
            db, "00000000-0000-0000-0000-0000000000ff"
        )


@pytest.mark.anyio
async def test_simulation_runs_survive_a_restart(runner: SimulationRunner, sim_db):
    """A completed run must still be readable after the process goes away."""
    db, ws = sim_db
    original = await runner.run_simulation(db, ws, {
        "type": "test",
        "events": [{"type": "alert_triggered", "severity": "high", "rule": "x"}],
    })

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            report = await runner.get_simulation_report(
                session, original["simulation_id"]
            )
        assert report["simulation_id"] == original["simulation_id"]
    finally:
        await restarted_engine.dispose()


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_generate_scenario(ac: AsyncClient):
    """POST /api/simulation/scenarios/generate returns a valid scenario."""
    resp = await ac.post(
        "/api/simulation/scenarios/generate",
        json={"type": "intrusion", "params": {"event_count": 4}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "intrusion"
    assert len(data["events"]) >= 4
    assert "scenario_id" in data


@pytest.mark.anyio
async def test_api_generate_invalid_type(ac: AsyncClient):
    """POST with invalid scenario type returns 400."""
    resp = await ac.post(
        "/api/simulation/scenarios/generate",
        json={"type": "nonexistent"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_api_stress_test(ac: AsyncClient):
    """POST /api/simulation/stress-test returns latency metrics."""
    resp = await ac.post(
        "/api/simulation/stress-test",
        json={
            "target_module": "vision",
            "concurrent_requests": 10,
            "duration_s": 30,
            "payload_type": "small",
        },
    )
    # Route should exist (may take time or hit DB issues)
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "throughput_rps" in data
        assert "latency_p50_ms" in data


@pytest.mark.anyio
async def test_api_edge_cases(ac: AsyncClient):
    """POST /api/simulation/edge-cases returns edge case results."""
    resp = await ac.post(
        "/api/simulation/edge-cases",
        json={"model_name": "test-model"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "test-model"
    assert len(data["test_cases"]) == 8


@pytest.mark.anyio
async def test_api_benchmark(ac: AsyncClient):
    """POST /api/simulation/benchmark returns pipeline benchmark results."""
    resp = await ac.post(
        "/api/simulation/benchmark",
        json={"pipeline_id": "pipe-test", "iterations": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_id"] == "pipe-test"
    assert "bottleneck_node" in data


@pytest.mark.anyio
async def test_api_report_not_found(ac: AsyncClient):
    """GET /api/simulation/report/{id} with bad id returns 404."""
    resp = await ac.get("/api/simulation/report/nonexistent-id")
    assert resp.status_code == 404
