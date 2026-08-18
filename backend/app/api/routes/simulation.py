"""Simulation Lab routes — scenario generation, simulation execution, reports."""

from __future__ import annotations

import random
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.simulation import SimulationRun as SimulationRunModel
from app.models.simulation import SimulationScenario

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _render_pdf(lines: list[str]) -> bytes:
    """Render text lines as a single-page PDF.

    Written by hand rather than pulling in a PDF library: the report is plain
    left-aligned text, and this keeps the dependency surface unchanged.
    """
    def _escape(text: str) -> str:
        return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    text_ops = ["BT", "/F1 11 Tf", "14 TL", "56 760 Td"]
    for line in lines:
        text_ops.append(f"({_escape(line)}) Tj")
        text_ops.append("T*")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


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


def _uuid_or_404(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{what} not found")


def _serialise_scenario(row: SimulationScenario) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "type": row.scenario_type,
        "parameters": (row.definition or {}).get("parameters", {}),
        "created_at": row.created_at.timestamp() if row.created_at else None,
    }


async def _load_scenario(db: AsyncSession, scenario_id: str) -> SimulationScenario:
    row = (
        await db.execute(
            select(SimulationScenario).where(
                SimulationScenario.id == _uuid_or_404(scenario_id, "Scenario")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return row


async def _load_run(db: AsyncSession, simulation_id: str, what: str = "Simulation"):
    row = (
        await db.execute(
            select(SimulationRunModel).where(
                SimulationRunModel.id == _uuid_or_404(simulation_id, what)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{what} not found")
    return row


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scenarios")
async def generate_scenario(
    body: ScenarioGenerate,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    row = SimulationScenario(
        workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
        name=body.name,
        scenario_type=body.scenario_type,
        definition={"parameters": body.parameters},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    scenario = _serialise_scenario(row)
    return scenario


@router.get("/scenarios")
async def list_scenarios(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    stmt = select(SimulationScenario)
    if workspace_id:
        stmt = stmt.where(
            SimulationScenario.workspace_id == uuid.UUID(str(workspace_id))
        )
    rows = (
        await db.execute(stmt.order_by(SimulationScenario.created_at))
    ).scalars().all()
    return [_serialise_scenario(r) for r in rows]


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    return _serialise_scenario(await _load_scenario(db, scenario_id))


@router.post("/run")
async def run_simulation(
    body: SimulationRun,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Record a simulation run against a saved scenario.

    No load is actually generated here. The results used to be the fixed
    numbers throughput=1250, p50=45ms, p99=120ms, error_rate=0.002, which are
    indistinguishable from a real measurement; they are reported as unmeasured
    instead. /api/simulation/runs is the endpoint that produces real numbers.
    """
    scenario = await _load_scenario(db, body.scenario_id)

    run = SimulationRunModel(
        workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
        scenario=scenario.definition or {},
        scenario_id=scenario.id,
        status="completed",
        result={
            "config": body.config,
            "results": None,
            "unmeasured": [
                "throughput",
                "latency_p50_ms",
                "latency_p99_ms",
                "error_rate",
            ],
            "detail": "This endpoint records a run; it does not generate load.",
        },
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return {
        "id": str(run.id),
        "scenario_id": str(scenario.id),
        "status": run.status,
        **(run.result or {}),
        "started_at": run.created_at.timestamp() if run.created_at else None,
        "completed_at": run.created_at.timestamp() if run.created_at else None,
    }


@router.post("/runs")
async def run_simulation_full(
    body: SimulationRunFull,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
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

    record = {
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
        # The events are synthesised from a seeded RNG, so the scores below
        # describe generated data, not observed behaviour.
        "simulated": True,
    }

    run = SimulationRunModel(
        workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
        scenario={"scenario_id": body.scenario_id},
        label=body.label,
        status="completed",
        events_injected=body.event_count,
        duration_s=body.duration_s,
        timeline=events,
        result=record,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return {
        "id": str(run.id),
        **record,
        "started_at": run.created_at.timestamp() if run.created_at else None,
        "completed_at": run.created_at.timestamp() if run.created_at else None,
    }


@router.get("/runs/{simulation_id}")
async def get_simulation_run(
    simulation_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Retrieve a completed simulation run by ID."""
    run = await _load_run(db, simulation_id, "Simulation run")
    return {
        "id": str(run.id),
        **(run.result or {}),
        "started_at": run.created_at.timestamp() if run.created_at else None,
        "completed_at": run.created_at.timestamp() if run.created_at else None,
    }


@router.post("/runs/{simulation_id}/report")
async def export_run_report(simulation_id: str) -> Response:
    """Export a simulation run's report as a downloadable PDF.

    The console POSTs here and saves the response body straight to disk, so the
    body must be the file itself rather than JSON.
    """
    report = await get_report(simulation_id)

    lines = [
        "VisionAudioForge — Simulation Report",
        "",
        f"Simulation: {report['simulation_id']}",
        f"Scenario:   {report['scenario']}",
        f"Status:     {report['status']}",
        "",
        report["summary"],
        "",
        "Results:",
    ]
    lines += [f"  {key}: {value}" for key, value in report["results"].items()]

    return Response(
        content=_render_pdf(lines),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="simulation-report-{simulation_id}.pdf"'
            )
        },
    )


@router.get("/report/{simulation_id}")
async def get_report(
    simulation_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    run = await _load_run(db, simulation_id)
    sim = dict(run.result or {})
    sim["status"] = run.status

    scenario: dict[str, Any] = {}
    if run.scenario_id:
        row = (
            await db.execute(
                select(SimulationScenario).where(
                    SimulationScenario.id == run.scenario_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            scenario = _serialise_scenario(row)

    results = sim.get("results") or {}
    error_rate = results.get("error_rate", 0)
    return {
        "simulation_id": simulation_id,
        "scenario": scenario.get("name", sim.get("label", "unknown")),
        "status": sim["status"],
        "results": results,
        "summary": f"Simulation completed with {error_rate*100:.1f}% error rate" if results else "Simulation completed",
    }
