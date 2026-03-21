"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

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

class EdgeCaseRequest(BaseModel):
    id: str
    name: str
    category: Literal["Vision", "Audio", "System"]
    custom: bool = False
    modification_type: str | None = None
    intensity: float | None = None


class EdgeCaseResponse(BaseModel):
    status: Literal["pass", "fail", "degraded"]
    scoreBefore: float
    scoreAfter: float
    confidenceDrop: float


class ScenarioGenerate(BaseModel):
    name: str
    scenario_type: str = "stress-test"
    parameters: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None


class SimulationRun(BaseModel):
    scenario_id: str
    config: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_scenarios: dict[str, dict] = {}
_simulations: dict[str, dict] = {}


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
# Edge-case testing (stub)
# ---------------------------------------------------------------------------

@router.post("/edge-case", response_model=EdgeCaseResponse)
async def run_edge_case(body: EdgeCaseRequest) -> EdgeCaseResponse:
    """Run an edge-case scenario and return a simulated pass/fail/degraded result."""
    score_before = round(random.uniform(0.80, 0.98), 4)

    # Harder edge cases get worse scores on average
    difficulty: dict[str, float] = {
        "low-light": 0.15,
        "heavy-occlusion": 0.25,
        "motion-blur": 0.12,
        "extreme-crowd": 0.30,
        "background-noise": 0.10,
        "silent-audio": 0.08,
        "very-long-audio": 0.05,
        "adversarial-image": 0.35,
        "out-of-distribution": 0.28,
        "network-dropout": 0.20,
    }
    base_drop = difficulty.get(body.id, 0.18)

    # Custom intensity amplifies the drop
    if body.custom and body.intensity is not None:
        base_drop = base_drop * (body.intensity / 50.0)

    drop = round(base_drop + random.uniform(-0.05, 0.05), 4)
    drop = max(0.0, min(drop, score_before))
    score_after = round(score_before - drop, 4)
    confidence_drop = round((drop / score_before) * 100, 1) if score_before > 0 else 0.0

    if confidence_drop < 10:
        status: Literal["pass", "fail", "degraded"] = "pass"
    elif confidence_drop < 25:
        status = "degraded"
    else:
        status = "fail"

    return EdgeCaseResponse(
        status=status,
        scoreBefore=score_before,
        scoreAfter=score_after,
        confidenceDrop=confidence_drop,
    )
