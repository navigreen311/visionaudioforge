"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

import math
import random
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScenarioGenerate(BaseModel):
    name: str
    scenario_type: str = "stress-test"
    parameters: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None


class SimulationRun(BaseModel):
    scenario_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class StressTestCreate(BaseModel):
    target: Literal["all_pipelines", "specific_pipeline", "api_endpoint"] = "all_pipelines"
    target_name: str = ""
    concurrency: int = Field(default=10, ge=1, le=100)
    ramp_up_seconds: int = Field(default=10, ge=0)
    duration_seconds: int = Field(default=60, ge=5)
    request_type: Literal["vision", "audio", "pipeline", "custom"] = "vision"


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_scenarios: dict[str, dict] = {}
_simulations: dict[str, dict] = {}
_stress_tests: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scenarios")
async def generate_scenario(body: ScenarioGenerate) -> dict[str, Any]:
    sid = str(uuid.uuid4())
    scenario = {
        "id": sid,
        "name": body.name,
        "type": body.scenario_type,
        "parameters": body.parameters,
        "created_at": time.time(),
    }
    _scenarios[sid] = scenario
    return scenario


@router.get("/scenarios")
async def list_scenarios() -> list[dict]:
    return list(_scenarios.values())


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict:
    if scenario_id not in _scenarios:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenarios[scenario_id]


@router.post("/run")
async def run_simulation(body: SimulationRun) -> dict[str, Any]:
    if body.scenario_id not in _scenarios:
        raise HTTPException(status_code=404, detail="Scenario not found")
    sim_id = str(uuid.uuid4())
    simulation = {
        "id": sim_id,
        "scenario_id": body.scenario_id,
        "status": "completed",
        "config": body.config,
        "results": {
            "throughput": 1250.0,
            "latency_p50_ms": 45.0,
            "latency_p99_ms": 120.0,
            "error_rate": 0.002,
            "duration_seconds": 60,
        },
        "started_at": time.time(),
        "completed_at": time.time(),
    }
    _simulations[sim_id] = simulation
    return simulation


@router.get("/report/{simulation_id}")
async def get_report(simulation_id: str) -> dict[str, Any]:
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim = _simulations[simulation_id]
    scenario = _scenarios.get(sim["scenario_id"], {})
    return {
        "simulation_id": simulation_id,
        "scenario": scenario.get("name", "unknown"),
        "status": sim["status"],
        "results": sim["results"],
        "summary": f"Simulation completed with {sim['results']['error_rate']*100:.1f}% error rate",
    }


# ---------------------------------------------------------------------------
# Stress-test stub helpers
# ---------------------------------------------------------------------------

def _generate_mock_stress_data(
    duration: int,
    concurrency: int,
) -> dict[str, Any]:
    """Build synthetic throughput, latency, and summary data."""
    points = min(duration, 60)
    throughput: list[dict[str, float]] = []
    latency: list[dict[str, float]] = []

    total_sent = 0
    total_completed = 0
    total_failed = 0
    peak_rps = 0.0
    latencies: list[float] = []

    for i in range(points):
        t = i / max(points - 1, 1)
        # Ramp-up curve
        load_factor = min(t * 3, 1.0)
        base_rps = concurrency * 12 * load_factor
        sent = int(base_rps + random.gauss(0, base_rps * 0.05))
        fail_rate = 0.02 + 0.01 * math.sin(t * math.pi)
        failed = max(0, int(sent * fail_rate))
        completed = sent - failed

        total_sent += sent
        total_completed += completed
        total_failed += failed
        peak_rps = max(peak_rps, float(sent))

        throughput.append({
            "ts": i,
            "sent": sent,
            "completed": completed,
            "failed": failed,
        })

        avg_ms = 35 + 15 * math.sin(t * 2 * math.pi) + random.gauss(0, 3)
        p95_ms = avg_ms * 2.2 + random.gauss(0, 5)
        p99_ms = avg_ms * 3.5 + random.gauss(0, 8)
        latencies.append(avg_ms)

        latency.append({
            "ts": i,
            "avg_ms": round(avg_ms, 1),
            "p95_ms": round(p95_ms, 1),
            "p99_ms": round(p99_ms, 1),
        })

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p99_final = latency[-1]["p99_ms"] if latency else 0

    summary = {
        "total_requests": total_sent,
        "successful": total_completed,
        "failed": total_failed,
        "rps_peak": round(peak_rps, 1),
        "avg_latency_ms": round(avg_latency, 1),
        "p99_latency_ms": round(p99_final, 1),
        "success_rate": round(total_completed / max(total_sent, 1) * 100, 2),
    }

    return {
        "throughput": throughput,
        "latency": latency,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Stress-test endpoints
# ---------------------------------------------------------------------------

@router.post("/stress-test")
async def create_stress_test(body: StressTestCreate) -> dict[str, Any]:
    """Start a new stress test (stub — returns mock data immediately)."""
    test_id = str(uuid.uuid4())
    mock = _generate_mock_stress_data(body.duration_seconds, body.concurrency)

    _stress_tests[test_id] = {
        "id": test_id,
        "config": body.model_dump(),
        "status": "completed",
        "elapsed_seconds": body.duration_seconds,
        "created_at": time.time(),
        **mock,
    }

    return {"id": test_id, "status": "completed"}


@router.get("/stress-test/{test_id}/status")
async def get_stress_test_status(test_id: str) -> dict[str, Any]:
    """Poll stress test progress / results."""
    if test_id not in _stress_tests:
        raise HTTPException(status_code=404, detail="Stress test not found")

    entry = _stress_tests[test_id]
    return {
        "id": test_id,
        "status": entry["status"],
        "elapsed_seconds": entry["elapsed_seconds"],
        "throughput": entry["throughput"],
        "latency": entry["latency"],
        "summary": entry["summary"],
    }
