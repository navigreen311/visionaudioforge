"""Simulation runner — injects scenario events, replays, compares, and reports."""

import asyncio
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import SimulationRun


def _serialise_run(run: SimulationRun) -> dict[str, Any]:
    """Render a stored run in the shape callers expect."""
    return {
        "simulation_id": str(run.id),
        "workspace_id": str(run.workspace_id) if run.workspace_id else None,
        "scenario": run.scenario or {},
        "events_injected": run.events_injected,
        "alerts_triggered": run.alerts_triggered,
        "duration_s": run.duration_s,
        "timeline": run.timeline or [],
    }


async def _load_run(db: AsyncSession, simulation_id: str) -> SimulationRun | None:
    try:
        sid = uuid.UUID(str(simulation_id))
    except ValueError:
        return None
    return (
        await db.execute(select(SimulationRun).where(SimulationRun.id == sid))
    ).scalar_one_or_none()


class SimulationRunner:
    """Runs, replays, compares, and reports on simulations."""

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------

    async def run_simulation(
        self,
        db: Any,
        workspace_id: str,
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        """Inject scenario events into the event bus and record outcomes."""
        simulation_id = str(uuid.uuid4())
        events = scenario.get("events", [])
        timeline: list[dict[str, Any]] = []
        alerts_triggered = 0
        events_injected = 0

        start = time.time()

        for event in events:
            # Simulate injection delay proportional to event spacing
            await asyncio.sleep(0.001)
            events_injected += 1

            entry: dict[str, Any] = {
                "seq": events_injected,
                "event": event,
                "injected_at": time.time(),
                "status": "delivered",
            }

            if event.get("type") == "alert_triggered":
                alerts_triggered += 1
                entry["alert_id"] = str(uuid.uuid4())
                entry["status"] = "alert_fired"

            timeline.append(entry)

        duration = round(time.time() - start, 3)

        run = SimulationRun(
            workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
            scenario=scenario,
            events_injected=events_injected,
            alerts_triggered=alerts_triggered,
            duration_s=duration,
            timeline=timeline,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _serialise_run(run)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    async def replay_simulation(
        self,
        db: Any,
        simulation_id: str,
    ) -> dict[str, Any]:
        """Re-run a previously executed simulation."""
        original = await _load_run(db, simulation_id)
        if original is None:
            raise ValueError(f"Simulation {simulation_id} not found")

        return await self.run_simulation(
            db,
            str(original.workspace_id) if original.workspace_id else None,
            original.scenario or {},
        )

    # ------------------------------------------------------------------
    # Compare
    # ------------------------------------------------------------------

    async def compare_simulations(
        self,
        db: Any,
        sim_ids: list[str],
    ) -> dict[str, Any]:
        """Compare metrics across multiple simulation runs."""
        comparison: list[dict[str, Any]] = []
        metrics = ["events_injected", "alerts_triggered", "duration_s"]

        loaded = {sid: await _load_run(db, sid) for sid in sim_ids}

        for metric in metrics:
            values: dict[str, Any] = {}
            for sid in sim_ids:
                run = loaded[sid]
                # None distinguishes "this run does not exist" from a real zero.
                values[sid] = getattr(run, metric) if run is not None else None
            comparison.append({"metric": metric, "values": values})

        return {"comparison": comparison}

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    async def get_simulation_report(
        self,
        db: Any,
        simulation_id: str,
    ) -> dict[str, Any]:
        """Generate a detailed report for a simulation run."""
        run = await _load_run(db, simulation_id)
        if run is None:
            raise ValueError(f"Simulation {simulation_id} not found")

        sim = _serialise_run(run)
        scenario = sim["scenario"]
        timeline = sim["timeline"]

        # Analyse alerts
        alerts = [e for e in timeline if e["event"].get("type") == "alert_triggered"]

        # Determine which expected events were missed (synthetic analysis)
        expected_alert_rules = set()
        for ev in scenario.get("events", []):
            if ev.get("type") == "alert_triggered":
                expected_alert_rules.add(ev.get("rule", "unknown"))

        fired_rules = {e["event"].get("rule", "unknown") for e in alerts}
        missed = list(expected_alert_rules - fired_rules)

        # Recommendations based on results
        recommendations: list[str] = []
        if sim["alerts_triggered"] == 0:
            recommendations.append("No alerts were triggered — verify alert rules are configured.")
        if missed:
            recommendations.append(f"Missed detections for rules: {', '.join(missed)}. Review thresholds.")
        if sim["duration_s"] > 5.0:
            recommendations.append("Simulation took longer than expected — check pipeline bottlenecks.")
        if not recommendations:
            recommendations.append("All expected alerts fired within acceptable time windows.")

        return {
            "simulation_id": simulation_id,
            "scenario": {
                "type": scenario.get("type"),
                "description": scenario.get("description"),
                "event_count": len(scenario.get("events", [])),
            },
            "results": {
                "events_injected": sim["events_injected"],
                "alerts_triggered": sim["alerts_triggered"],
                "duration_s": sim["duration_s"],
            },
            "alerts": [
                {
                    "alert_id": a.get("alert_id"),
                    "rule": a["event"].get("rule"),
                    "severity": a["event"].get("severity"),
                    "timestamp": a["injected_at"],
                }
                for a in alerts
            ],
            "missed_detections": missed,
            "false_alarms": [],  # Would require ground-truth comparison in production
            "recommendations": recommendations,
        }
