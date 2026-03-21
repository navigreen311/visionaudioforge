"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

import random
import time
import uuid
from typing import Any

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


class SimulationRunFull(BaseModel):
    """Run a simulation directly from scenario config (no pre-created scenario needed)."""
    scenario_id: str
    label: str = ""
    event_count: int = Field(default=10, ge=1, le=200)
    duration_s: int = Field(default=30, ge=5, le=600)
    noise_level: float = Field(default=0.1, ge=0.0, le=1.0)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    random_seed: int = 42


# ---------------------------------------------------------------------------
# Event type mapping per scenario
# ---------------------------------------------------------------------------

_SCENARIO_EVENT_TYPES: dict[str, list[str]] = {
    "intrusion_detection": ["person_detected", "motion_alert", "perimeter_breach", "loitering"],
    "vehicle_tracking": ["vehicle_enter", "vehicle_tracked", "license_plate_read", "speed_violation"],
    "crowd_monitoring": ["crowd_count", "density_spike", "flow_change", "overcrowding"],
    "package_abandoned": ["object_stationary", "unattended_timer", "abandoned_alert", "object_removed"],
    "audio_anomaly": ["audio_classified", "anomaly_detected", "glass_break", "gunshot_detected"],
    "ocr_document": ["text_region_found", "ocr_result", "document_classified", "verification_pass"],
    "multi_zone_handoff": ["track_started", "zone_exit", "re_id_match", "handoff_complete"],
    "system_stress": ["request_sent", "response_received", "timeout", "error_500"],
}

_PIPELINES: dict[str, str] = {
    "intrusion_detection": "vision-yolov8",
    "vehicle_tracking": "vision-deepsort",
    "crowd_monitoring": "vision-crowdnet",
    "package_abandoned": "vision-stationary",
    "audio_anomaly": "audio-mel-classifier",
    "ocr_document": "vision-tesseract",
    "multi_zone_handoff": "vision-reid",
    "system_stress": "pipeline-load",
}


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


@router.post("/runs")
async def run_simulation_full(body: SimulationRunFull) -> dict[str, Any]:
    """Run a full simulation from scenario config — generates synthetic events."""
    rng = random.Random(body.random_seed)
    event_types = _SCENARIO_EVENT_TYPES.get(body.scenario_id, ["generic_event"])
    pipeline = _PIPELINES.get(body.scenario_id, "pipeline-default")

    events: list[dict[str, Any]] = []
    detections = 0
    false_alarms = 0
    missed = 0

    for i in range(body.event_count):
        offset = round((body.duration_s / max(body.event_count, 1)) * i, 2)
        confidence = round(max(0.0, min(1.0, rng.gauss(0.75, body.noise_level))), 3)
        etype = rng.choice(event_types)
        alert = confidence >= body.confidence_threshold and rng.random() > 0.3

        if alert:
            detections += 1
        if confidence < body.confidence_threshold and rng.random() < 0.15:
            false_alarms += 1
            alert = True
        if confidence >= body.confidence_threshold and not alert:
            missed += 1

        severity = None
        if alert:
            severity = rng.choice(["low", "medium", "high", "critical"])

        events.append({
            "seq": i + 1,
            "type": etype,
            "timestamp_offset": offset,
            "pipeline": pipeline,
            "confidence": confidence,
            "alert_triggered": alert,
            "severity": severity,
        })

    total = body.event_count
    robustness = max(0, min(100, round(
        100 * (detections / max(total, 1))
        - 20 * (false_alarms / max(total, 1))
        - 30 * (missed / max(total, 1))
    )))

    sim_id = str(uuid.uuid4())
    simulation = {
        "id": sim_id,
        "scenario_id": body.scenario_id,
        "label": body.label,
        "status": "completed",
        "event_count": body.event_count,
        "duration_s": body.duration_s,
        "events": events,
        "robustness_score": robustness,
        "detections": detections,
        "false_alarms": false_alarms,
        "missed": missed,
        "total_events": total,
        "started_at": time.time(),
        "completed_at": time.time(),
    }
    _simulations[sim_id] = simulation
    return simulation


@router.get("/runs/{simulation_id}")
async def get_simulation_run(simulation_id: str) -> dict[str, Any]:
    """Retrieve a completed simulation run by ID."""
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return _simulations[simulation_id]


@router.get("/report/{simulation_id}")
async def get_report(simulation_id: str) -> dict[str, Any]:
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim = _simulations[simulation_id]
    scenario = _scenarios.get(sim.get("scenario_id", ""), {})
    results = sim.get("results", {})
    error_rate = results.get("error_rate", 0)
    return {
        "simulation_id": simulation_id,
        "scenario": scenario.get("name", sim.get("label", "unknown")),
        "status": sim["status"],
        "results": results,
        "summary": f"Simulation completed with {error_rate*100:.1f}% error rate" if results else "Simulation completed",
    }
