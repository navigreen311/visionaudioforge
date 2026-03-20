"""Federated Learning coordinator — manages federations, rounds, and updates."""

from __future__ import annotations

import base64
import io
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.services.federated.aggregation import FederatedAggregator
from app.services.federated.privacy import DifferentialPrivacy


class FederatedCoordinator:
    """Orchestrates federated learning across multiple participants."""

    def __init__(self) -> None:
        self._federations: dict[str, dict] = {}
        self._aggregator = FederatedAggregator()
        self._privacy = DifferentialPrivacy()

    # ------------------------------------------------------------------
    # Federation lifecycle
    # ------------------------------------------------------------------

    async def create_federation(
        self,
        db: Any,
        workspace_id: str,
        name: str,
        model_id: str,
        config: dict | None = None,
    ) -> dict:
        """Create a new federation for collaborative training."""
        default_config = {
            "min_participants": 2,
            "max_rounds": 50,
            "aggregation_method": "fedavg",
            "privacy_budget": 1.0,
            "min_samples_per_participant": 100,
        }
        merged = {**default_config, **(config or {})}
        federation_id = str(uuid.uuid4())
        self._federations[federation_id] = {
            "id": federation_id,
            "workspace_id": workspace_id,
            "name": name,
            "model_id": model_id,
            "config": merged,
            "status": "created",
            "participants": [],
            "rounds": [],
            "current_round": 0,
            "global_model": None,
            "metrics_history": [],
            "epsilon_spent": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return {
            "federation_id": federation_id,
            "name": name,
            "status": "created",
            "config": merged,
        }

    async def join_federation(
        self,
        db: Any,
        federation_id: str,
        participant_id: str,
        participant_info: dict | None = None,
    ) -> dict:
        """Register a participant in the federation."""
        fed = self._get_federation(federation_id)
        if any(p["id"] == participant_id for p in fed["participants"]):
            return {"joined": False, "participant_count": len(fed["participants"])}

        fed["participants"].append(
            {
                "id": participant_id,
                "info": participant_info or {},
                "joined_at": datetime.now(timezone.utc).isoformat(),
                "status": "active",
            }
        )
        return {"joined": True, "participant_count": len(fed["participants"])}

    async def start_round(self, db: Any, federation_id: str) -> dict:
        """Start a new training round — distribute global model to participants."""
        fed = self._get_federation(federation_id)
        config = fed["config"]

        if len(fed["participants"]) < config["min_participants"]:
            raise ValueError(
                f"Need at least {config['min_participants']} participants, "
                f"have {len(fed['participants'])}"
            )

        if fed["current_round"] >= config["max_rounds"]:
            raise ValueError("Maximum rounds reached")

        if self._privacy.is_budget_exhausted(
            fed["epsilon_spent"], config["privacy_budget"]
        ):
            raise ValueError("Privacy budget exhausted")

        fed["current_round"] += 1
        round_id = str(uuid.uuid4())
        global_version = f"v{fed['current_round']}"
        round_info = {
            "round_id": round_id,
            "round_number": fed["current_round"],
            "global_model_version": global_version,
            "updates": [],
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        fed["rounds"].append(round_info)
        fed["status"] = "training"

        return {
            "round_id": round_id,
            "round_number": fed["current_round"],
            "global_model_version": global_version,
            "instructions": {
                "action": "train_local_model",
                "min_samples": config["min_samples_per_participant"],
                "global_weights": self._serialize_model(fed["global_model"]),
            },
        }

    async def submit_update(
        self,
        db: Any,
        federation_id: str,
        round_id: str,
        participant_id: str,
        model_update: dict,
        metrics: dict | None = None,
    ) -> dict:
        """Receive a model update from a participant."""
        fed = self._get_federation(federation_id)
        current_round = self._get_round(fed, round_id)

        if any(u["participant_id"] == participant_id for u in current_round["updates"]):
            raise ValueError("Participant already submitted for this round")

        # Deserialize weight deltas
        deserialized = self._deserialize_update(model_update)

        # Apply differential privacy noise
        config = fed["config"]
        epsilon_per_round = config["privacy_budget"] / max(config["max_rounds"], 1)
        noised = self._privacy.add_noise(
            deserialized, epsilon=epsilon_per_round, clip_norm=1.0
        )

        current_round["updates"].append(
            {
                "participant_id": participant_id,
                "update": noised,
                "metrics": metrics or {},
                "sample_count": (metrics or {}).get("sample_count", 1),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        fed["epsilon_spent"] += epsilon_per_round

        updates_needed = len(fed["participants"])
        return {
            "received": True,
            "updates_so_far": len(current_round["updates"]),
            "updates_needed": updates_needed,
        }

    async def aggregate_round(
        self, db: Any, federation_id: str, round_id: str
    ) -> dict:
        """Aggregate all participant updates for the round using FedAvg."""
        fed = self._get_federation(federation_id)
        current_round = self._get_round(fed, round_id)

        if not current_round["updates"]:
            raise ValueError("No updates to aggregate")

        updates = [u["update"] for u in current_round["updates"]]
        weights = [float(u["sample_count"]) for u in current_round["updates"]]

        method = fed["config"]["aggregation_method"]
        if method == "fedprox":
            aggregated = self._aggregator.fedprox(
                updates, weights, global_model=fed["global_model"] or {}
            )
        elif method == "trimmed_mean":
            aggregated = self._aggregator.trimmed_mean(updates, weights)
        else:
            aggregated = self._aggregator.fedavg(updates, weights)

        fed["global_model"] = aggregated
        current_round["status"] = "completed"

        # Compute average metrics
        all_metrics = [u["metrics"] for u in current_round["updates"] if u["metrics"]]
        avg_metrics = self._average_metrics(all_metrics)
        fed["metrics_history"].append(
            {
                "round": fed["current_round"],
                "metrics": avg_metrics,
                "participants": len(current_round["updates"]),
            }
        )

        new_version = f"v{fed['current_round']}-aggregated"
        return {
            "new_global_version": new_version,
            "participants": len(current_round["updates"]),
            "avg_metrics": avg_metrics,
            "round_complete": True,
        }

    async def get_federation_status(self, db: Any, federation_id: str) -> dict:
        """Return current federation status."""
        fed = self._get_federation(federation_id)
        return {
            "status": fed["status"],
            "current_round": fed["current_round"],
            "participants": [
                {"id": p["id"], "status": p["status"]} for p in fed["participants"]
            ],
            "metrics_history": fed["metrics_history"],
        }

    async def stop_federation(self, db: Any, federation_id: str) -> dict:
        """Stop the federation and return final results."""
        fed = self._get_federation(federation_id)
        fed["status"] = "stopped"
        final_metrics = (
            fed["metrics_history"][-1]["metrics"] if fed["metrics_history"] else {}
        )
        return {
            "stopped": True,
            "total_rounds": fed["current_round"],
            "final_metrics": final_metrics,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_federation(self, federation_id: str) -> dict:
        if federation_id not in self._federations:
            raise ValueError(f"Federation {federation_id} not found")
        return self._federations[federation_id]

    def _get_round(self, fed: dict, round_id: str) -> dict:
        for r in fed["rounds"]:
            if r["round_id"] == round_id:
                return r
        raise ValueError(f"Round {round_id} not found")

    @staticmethod
    def _serialize_model(model: dict | None) -> dict | None:
        if model is None:
            return None
        serialized: dict[str, str] = {}
        for key, val in model.items():
            buf = io.BytesIO()
            np.save(buf, val)
            serialized[key] = base64.b64encode(buf.getvalue()).decode()
        return serialized

    @staticmethod
    def _deserialize_update(model_update: dict) -> dict:
        deserialized: dict[str, np.ndarray] = {}
        for key, val in model_update.items():
            if isinstance(val, str):
                buf = io.BytesIO(base64.b64decode(val))
                deserialized[key] = np.load(buf)
            elif isinstance(val, np.ndarray):
                deserialized[key] = val
            else:
                deserialized[key] = np.array(val)
        return deserialized

    @staticmethod
    def _average_metrics(metrics_list: list[dict]) -> dict:
        if not metrics_list:
            return {}
        keys = set()
        for m in metrics_list:
            keys.update(m.keys())
        avg: dict[str, float] = {}
        for k in keys:
            vals = [m[k] for m in metrics_list if k in m and isinstance(m[k], (int, float))]
            if vals:
                avg[k] = sum(vals) / len(vals)
        return avg
