"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
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
# Run History & PDF Report endpoints (SI5)
# ---------------------------------------------------------------------------

def _build_stub_runs() -> list[dict[str, Any]]:
    """Return deterministic stub data for the run history table."""
    now = datetime.now(timezone.utc)
    run_types: list[str] = ["scenario", "stress", "edge-case"]
    severities: list[str] = ["info", "warning", "error", "critical"]
    stubs: list[dict[str, Any]] = []
    for i in range(8):
        rid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"stub-run-{i}"))
        rtype = run_types[i % len(run_types)]
        score = max(0, min(100, 60 + (i * 7) % 41))
        created = (now - timedelta(days=i, hours=i * 3)).isoformat()
        event_count = 3 + i
        events = [
            {
                "timestamp": (
                    now - timedelta(days=i, hours=i * 3, minutes=j * 2)
                ).isoformat(),
                "type": "pipeline_event",
                "message": f"Event {j + 1} for run {i + 1}",
                "severity": severities[j % len(severities)],
            }
            for j in range(event_count)
        ]
        stubs.append(
            {
                "id": rid,
                "name": f"Run {i + 1} — {rtype.replace('-', ' ').title()}",
                "type": rtype,
                "score": score,
                "events": event_count,
                "duration_seconds": 30 + i * 15,
                "created_at": created,
                "status": "completed" if i != 2 else "failed",
                "event_log": events,
            }
        )
    return stubs


@router.get("/runs")
async def list_runs() -> list[dict[str, Any]]:
    """Return all simulation runs (stub data + any runs from in-memory store)."""
    runs: list[dict[str, Any]] = _build_stub_runs()
    # Append any runs created via /run endpoint
    for sim_id, sim in _simulations.items():
        scenario = _scenarios.get(sim["scenario_id"], {})
        runs.append(
            {
                "id": sim_id,
                "name": scenario.get("name", f"Run {sim_id[:8]}"),
                "type": scenario.get("type", "scenario"),
                "score": round(random.uniform(50, 100)),
                "events": 0,
                "duration_seconds": int(
                    sim.get("results", {}).get("duration_seconds", 60)
                ),
                "created_at": datetime.fromtimestamp(
                    sim.get("started_at", time.time()), tz=timezone.utc
                ).isoformat(),
                "status": sim.get("status", "completed"),
                "event_log": [],
            }
        )
    return runs


@router.post("/runs/{run_id}/report")
async def export_run_report(run_id: str) -> JSONResponse:
    """Generate a report for a simulation run (stub — returns JSON payload).

    In production this would generate a PDF.  For now returns a JSON
    report with Content-Type application/json so the frontend can
    handle the download.
    """
    # Look in dynamic store first
    sim = _simulations.get(run_id)
    if sim:
        scenario = _scenarios.get(sim["scenario_id"], {})
        return JSONResponse(
            {
                "report": {
                    "run_id": run_id,
                    "name": scenario.get("name", "unknown"),
                    "status": sim["status"],
                    "results": sim["results"],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        )
    # Check stub runs
    for stub in _build_stub_runs():
        if stub["id"] == run_id:
            return JSONResponse(
                {
                    "report": {
                        "run_id": run_id,
                        "name": stub["name"],
                        "type": stub["type"],
                        "score": stub["score"],
                        "events": stub["events"],
                        "duration_seconds": stub["duration_seconds"],
                        "status": stub["status"],
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                }
            )
    raise HTTPException(status_code=404, detail="Run not found")
