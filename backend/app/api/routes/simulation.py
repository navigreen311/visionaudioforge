"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
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


class SimulationRunRequest(BaseModel):
    """Body for the simplified POST /run endpoint."""
    scenario_type: str = "detection"
    duration_sec: int = 60
    parameters: dict[str, Any] = Field(default_factory=dict)


class StressTestRequest(BaseModel):
    """Body for POST /stress-test."""
    target: str = "pipeline"
    concurrency: int = 50
    duration_sec: int = 30
    parameters: dict[str, Any] = Field(default_factory=dict)


class EdgeCaseRequest(BaseModel):
    """Body for POST /edge-case."""
    case_name: str = "low_light_noise_burst"
    parameters: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_scenarios: dict[str, dict] = {}
_simulations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

_MOCK_EVENTS = [
    {"event_num": 1, "type": "anomaly_detected", "timestamp_offset_sec": 3.2, "triggered_alert": True},
    {"event_num": 2, "type": "normal_activity", "timestamp_offset_sec": 7.5, "triggered_alert": False},
    {"event_num": 3, "type": "anomaly_detected", "timestamp_offset_sec": 12.1, "triggered_alert": True},
    {"event_num": 4, "type": "anomaly_detected", "timestamp_offset_sec": 18.4, "triggered_alert": True},
    {"event_num": 5, "type": "false_positive", "timestamp_offset_sec": 22.0, "triggered_alert": True},
    {"event_num": 6, "type": "anomaly_detected", "timestamp_offset_sec": 30.7, "triggered_alert": True},
    {"event_num": 7, "type": "anomaly_detected", "timestamp_offset_sec": 38.9, "triggered_alert": True},
    {"event_num": 8, "type": "missed_anomaly", "timestamp_offset_sec": 45.3, "triggered_alert": False},
]

_MOCK_RUNS = [
    {"run_id": f"sim_{str(i).zfill(3)}", "status": "completed", "total_events": 8,
     "score": 76, "created_at": 1700000000 + i * 3600}
    for i in range(1, 6)
]


def _build_stress_summary() -> dict[str, Any]:
    return {
        "total": 1000,
        "successful": 950,
        "failed": 50,
        "rps_peak": 42.5,
        "avg_latency_ms": 85.3,
        "p99_latency_ms": 234.1,
        "passed": True,
    }


def _build_throughput_series() -> list[dict[str, Any]]:
    return [
        {"time_sec": t, "rps": 30 + t * 1.2}
        for t in range(0, 31, 5)
    ]


def _build_latency_series() -> list[dict[str, Any]]:
    return [
        {"time_sec": t, "p50_ms": 40 + t, "p99_ms": 100 + t * 4}
        for t in range(0, 31, 5)
    ]


# ---------------------------------------------------------------------------
# Existing endpoints — scenarios (unchanged)
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


# ---------------------------------------------------------------------------
# Existing endpoint — run with scenario_id (unchanged)
# ---------------------------------------------------------------------------

@router.post("/run/scenario")
async def run_simulation_with_scenario(body: SimulationRun) -> dict[str, Any]:
    """Run a simulation against a previously created scenario."""
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


# ---------------------------------------------------------------------------
# Existing endpoint — report (unchanged)
# ---------------------------------------------------------------------------

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
# NEW: POST /run — simplified simulation run (mock)
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_simulation(body: SimulationRunRequest) -> dict[str, Any]:
    """Run a simulation and return mock summary."""
    return {
        "run_id": "sim_001",
        "status": "completed",
        "total_events": 8,
    }


# ---------------------------------------------------------------------------
# NEW: GET /runs/{run_id} — detailed run results (mock)
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Get detailed results for a simulation run."""
    return {
        "run_id": run_id,
        "status": "completed",
        "events": _MOCK_EVENTS,
        "score": 76,
        "detection_rate": 0.875,
        "false_alarm_rate": 0.125,
        "missed_events": 1,
    }


# ---------------------------------------------------------------------------
# NEW: GET /runs — list past runs (mock)
# ---------------------------------------------------------------------------

@router.get("/runs")
async def list_runs() -> list[dict[str, Any]]:
    """List recent simulation runs."""
    return _MOCK_RUNS


# ---------------------------------------------------------------------------
# NEW: POST /stress-test — launch stress test (mock)
# ---------------------------------------------------------------------------

@router.post("/stress-test")
async def run_stress_test(body: StressTestRequest) -> dict[str, Any]:
    """Launch a stress test and return mock summary."""
    return {
        "test_id": "stress_001",
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# NEW: GET /stress-test/{test_id}/status — stress test status (mock)
# ---------------------------------------------------------------------------

@router.get("/stress-test/{test_id}/status")
async def get_stress_test_status(test_id: str) -> dict[str, Any]:
    """Get status and results of a stress test."""
    return {
        "test_id": test_id,
        "status": "completed",
        "throughput": _build_throughput_series(),
        "latency": _build_latency_series(),
        "summary": _build_stress_summary(),
    }


# ---------------------------------------------------------------------------
# NEW: POST /edge-case — run edge case test (mock)
# ---------------------------------------------------------------------------

@router.post("/edge-case")
async def run_edge_case(body: EdgeCaseRequest) -> dict[str, Any]:
    """Run an edge-case scenario and return mock result."""
    return {
        "case_name": body.case_name,
        "result": "degraded",
        "score_before": 92,
        "score_after": 71,
        "confidence_drop": 21,
    }


# ---------------------------------------------------------------------------
# NEW: POST /runs/{run_id}/report — generate plain text report (mock)
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/report")
async def generate_run_report(run_id: str) -> PlainTextResponse:
    """Generate a plain-text report for a simulation run."""
    report = (
        f"SIMULATION REPORT — {run_id}\n"
        f"{'=' * 40}\n"
        f"Status: completed\n"
        f"Total Events: 8\n"
        f"Score: 76 / 100\n"
        f"Detection Rate: 87.5%\n"
        f"False Alarm Rate: 12.5%\n"
        f"Missed Events: 1\n"
        f"\n"
        f"EVENT LOG:\n"
        f"  #1  anomaly_detected   @ 3.2s   [ALERT]\n"
        f"  #2  normal_activity    @ 7.5s   [—]\n"
        f"  #3  anomaly_detected   @ 12.1s  [ALERT]\n"
        f"  #4  anomaly_detected   @ 18.4s  [ALERT]\n"
        f"  #5  false_positive     @ 22.0s  [ALERT]\n"
        f"  #6  anomaly_detected   @ 30.7s  [ALERT]\n"
        f"  #7  anomaly_detected   @ 38.9s  [ALERT]\n"
        f"  #8  missed_anomaly     @ 45.3s  [—]\n"
        f"\n"
        f"SUMMARY: 7/8 events detected. 1 false alarm. 1 miss.\n"
    )
    return PlainTextResponse(content=report)
