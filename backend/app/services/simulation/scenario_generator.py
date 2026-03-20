"""Scenario generator — creates synthetic incident event sequences for simulation."""

import random
import time
import uuid
from typing import Any


class ScenarioGenerator:
    """Generates synthetic incident scenarios for simulation testing."""

    SCENARIO_TYPES = [
        "intrusion",
        "equipment_failure",
        "crowd_formation",
        "fire_smoke",
        "package_left",
        "medical_emergency",
    ]

    DIFFICULTY_PARAMS: dict[str, dict[str, Any]] = {
        "easy": {"noise": 0.05, "event_count_range": (3, 6), "duration_range": (10, 30)},
        "medium": {"noise": 0.15, "event_count_range": (5, 12), "duration_range": (20, 60)},
        "hard": {"noise": 0.30, "event_count_range": (10, 25), "duration_range": (30, 120)},
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_scenario(
        self,
        scenario_type: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a single scenario of the given type.

        Returns dict with scenario_id, type, events, duration_s, description.
        """
        if scenario_type not in self.SCENARIO_TYPES:
            raise ValueError(
                f"Unknown scenario type '{scenario_type}'. "
                f"Choose from: {', '.join(self.SCENARIO_TYPES)}"
            )

        params = params or {}
        builder = getattr(self, f"_build_{scenario_type}")
        events, duration, description = builder(params)

        return {
            "scenario_id": str(uuid.uuid4()),
            "type": scenario_type,
            "events": events,
            "duration_s": duration,
            "description": description,
        }

    def generate_random_scenario(self, difficulty: str = "medium") -> dict[str, Any]:
        """Generate a random scenario with randomized parameters."""
        scenario_type = random.choice(self.SCENARIO_TYPES)
        diff = self.DIFFICULTY_PARAMS.get(difficulty, self.DIFFICULTY_PARAMS["medium"])
        params = {
            "noise": diff["noise"],
            "event_count": random.randint(*diff["event_count_range"]),
            "duration_s": random.uniform(*diff["duration_range"]),
        }
        return self.generate_scenario(scenario_type, params)

    def generate_scenario_batch(
        self,
        types: list[str],
        count_per_type: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate multiple scenarios for each requested type."""
        results: list[dict[str, Any]] = []
        for t in types:
            for _ in range(count_per_type):
                results.append(self.generate_scenario(t))
        return results

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    @staticmethod
    def _ts(offset: float) -> float:
        return round(time.time() + offset, 3)

    def _build_intrusion(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        count = params.get("event_count", 8)
        duration = params.get("duration_s", 30.0)
        noise = params.get("noise", 0.1)
        zones = ["perimeter-north", "perimeter-east", "perimeter-south", "perimeter-west"]
        zone = random.choice(zones)
        events: list[dict[str, Any]] = []
        for i in range(count):
            t = (i / max(count - 1, 1)) * duration
            confidence = min(0.3 + (i / max(count - 1, 1)) * 0.65 + random.uniform(-noise, noise), 1.0)
            events.append({
                "timestamp": self._ts(t),
                "type": "motion_detected",
                "zone": zone,
                "confidence": round(confidence, 4),
                "metadata": {"frame_idx": i * 30, "bbox": [random.randint(0, 500) for _ in range(4)]},
            })
        # Final alert event
        events.append({
            "timestamp": self._ts(duration),
            "type": "alert_triggered",
            "severity": "high",
            "rule": "intrusion_perimeter",
            "zone": zone,
        })
        return events, duration, f"Simulated intrusion at {zone} with {count} motion events over {duration}s"

    def _build_equipment_failure(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        count = params.get("event_count", 6)
        duration = params.get("duration_s", 45.0)
        anomaly_types = ["vibration_spike", "temperature_rise", "noise_change"]
        events: list[dict[str, Any]] = []
        for i in range(count):
            t = (i / max(count - 1, 1)) * duration
            atype = anomaly_types[i % len(anomaly_types)]
            severity_val = 0.2 + (i / max(count - 1, 1)) * 0.7
            events.append({
                "timestamp": self._ts(t),
                "type": "anomaly_detected",
                "anomaly_type": atype,
                "severity": round(severity_val, 4),
                "equipment_id": params.get("equipment_id", "pump-unit-07"),
            })
        events.append({
            "timestamp": self._ts(duration),
            "type": "alert_triggered",
            "severity": "critical",
            "rule": "equipment_cascade_failure",
        })
        return events, duration, f"Simulated equipment failure cascade with {count} anomaly events"

    def _build_crowd_formation(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        count = params.get("event_count", 10)
        duration = params.get("duration_s", 60.0)
        events: list[dict[str, Any]] = []
        for i in range(count):
            t = (i / max(count - 1, 1)) * duration
            person_count = 2 + int((i / max(count - 1, 1)) * 48)
            events.append({
                "timestamp": self._ts(t),
                "type": "object_detection",
                "class": "person",
                "count": person_count,
                "zone": params.get("zone", "plaza-main"),
                "density": round(person_count / 50.0, 4),
            })
        events.append({
            "timestamp": self._ts(duration),
            "type": "alert_triggered",
            "severity": "warning",
            "rule": "crowd_threshold_exceeded",
        })
        return events, duration, f"Simulated crowd formation building to {2 + 48} persons"

    def _build_fire_smoke(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        count = params.get("event_count", 6)
        duration = params.get("duration_s", 20.0)
        events: list[dict[str, Any]] = []
        for i in range(count):
            t = (i / max(count - 1, 1)) * duration
            confidence = min(0.4 + (i / max(count - 1, 1)) * 0.55, 1.0)
            events.append({
                "timestamp": self._ts(t),
                "type": "visual_anomaly",
                "anomaly_class": "smoke" if i % 2 == 0 else "fire",
                "confidence": round(confidence, 4),
                "zone": params.get("zone", "warehouse-b"),
            })
            events.append({
                "timestamp": self._ts(t + 0.1),
                "type": "audio_anomaly",
                "anomaly_class": "alarm_sound",
                "confidence": round(confidence * 0.9, 4),
            })
        events.append({
            "timestamp": self._ts(duration),
            "type": "alert_triggered",
            "severity": "critical",
            "rule": "fire_smoke_detected",
        })
        return events, duration, "Simulated fire/smoke with visual + audio anomalies"

    def _build_package_left(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        duration = params.get("duration_s", 90.0)
        timeout = params.get("timeout_s", 60.0)
        events: list[dict[str, Any]] = [
            {
                "timestamp": self._ts(0),
                "type": "object_detection",
                "class": "bag",
                "confidence": 0.85,
                "zone": params.get("zone", "lobby-entrance"),
                "bbox": [120, 340, 180, 400],
            },
            {
                "timestamp": self._ts(5),
                "type": "object_stationary",
                "class": "bag",
                "stationary_since": self._ts(0),
                "zone": params.get("zone", "lobby-entrance"),
            },
            {
                "timestamp": self._ts(timeout),
                "type": "alert_triggered",
                "severity": "high",
                "rule": "unattended_package",
                "stationary_duration_s": timeout,
            },
        ]
        return events, duration, f"Simulated unattended package detected after {timeout}s timeout"

    def _build_medical_emergency(self, params: dict[str, Any]) -> tuple[list[dict], float, str]:
        duration = params.get("duration_s", 25.0)
        events: list[dict[str, Any]] = [
            {
                "timestamp": self._ts(0),
                "type": "object_detection",
                "class": "person",
                "confidence": 0.92,
                "zone": params.get("zone", "corridor-3"),
                "action": "walking",
            },
            {
                "timestamp": self._ts(5),
                "type": "action_detection",
                "class": "fall",
                "confidence": 0.88,
                "zone": params.get("zone", "corridor-3"),
            },
            {
                "timestamp": self._ts(7),
                "type": "object_detection",
                "class": "person",
                "confidence": 0.94,
                "zone": params.get("zone", "corridor-3"),
                "action": "lying_down",
                "motion": False,
            },
            {
                "timestamp": self._ts(10),
                "type": "alert_triggered",
                "severity": "critical",
                "rule": "medical_emergency_fall",
            },
        ]
        return events, duration, "Simulated medical emergency: person fall detected"
