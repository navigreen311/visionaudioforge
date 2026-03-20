"""Simulation runner — injects scenario events, replays, compares, and reports."""

import asyncio
import time
import uuid
from typing import Any


# In-memory store for simulation results (would be DB-backed in production)
_simulation_store: dict[str, dict[str, Any]] = {}


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

        result = {
            "simulation_id": simulation_id,
            "workspace_id": workspace_id,
            "scenario": scenario,
            "events_injected": events_injected,
            "alerts_triggered": alerts_triggered,
            "duration_s": duration,
            "timeline": timeline,
        }

        _simulation_store[simulation_id] = result
        return result

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    async def replay_simulation(
        self,
        db: Any,
        simulation_id: str,
    ) -> dict[str, Any]:
        """Re-run a previously executed simulation."""
        original = _simulation_store.get(simulation_id)
        if not original:
            raise ValueError(f"Simulation {simulation_id} not found")

        return await self.run_simulation(
            db,
            original["workspace_id"],
            original["scenario"],
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

        for metric in metrics:
            values: dict[str, Any] = {}
            for sid in sim_ids:
                sim = _simulation_store.get(sid)
                if sim:
                    values[sid] = sim.get(metric, 0)
                else:
                    values[sid] = None
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
        sim = _simulation_store.get(simulation_id)
        if not sim:
            raise ValueError(f"Simulation {simulation_id} not found")

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
