"""Federated Learning coordinator — manages federations, rounds, and updates.

Backed by the ``federations`` / ``federation_participants`` /
``federation_rounds`` tables. This held everything in a module-level dict, so a
federation and every round it had run vanished on restart, and no two workers
agreed on whose updates had arrived.

Submitted weights are stored on the round rather than kept in process memory:
``submit_update`` and ``aggregate_round`` are separate requests, so a worker
that never received the submissions still has to be able to aggregate them.
"""

from __future__ import annotations

import base64
import io
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.federated import (
    Federation,
    FederationParticipant,
    FederationRound,
    FederationStatus,
    ParticipantStatus,
    RoundStatus,
)
from app.services.federated.aggregation import FederatedAggregator
from app.services.federated.privacy import DifferentialPrivacy

DEFAULT_CONFIG: dict[str, Any] = {
    "min_participants": 2,
    "max_rounds": 50,
    "aggregation_method": "fedavg",
    "privacy_budget": 1.0,
    "min_samples_per_participant": 100,
}


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _encode(model: dict | None) -> dict | None:
    """Base64-encode numpy arrays so weights can live in a JSON column."""
    if model is None:
        return None
    encoded: dict[str, str] = {}
    for key, val in model.items():
        buf = io.BytesIO()
        np.save(buf, np.asarray(val))
        encoded[key] = base64.b64encode(buf.getvalue()).decode()
    return encoded


def _decode(payload: dict | None) -> dict:
    """Inverse of :func:`_encode`."""
    if not payload:
        return {}
    decoded: dict[str, np.ndarray] = {}
    for key, val in payload.items():
        if isinstance(val, str):
            decoded[key] = np.load(io.BytesIO(base64.b64decode(val)))
        elif isinstance(val, np.ndarray):
            decoded[key] = val
        else:
            decoded[key] = np.array(val)
    return decoded


class FederatedCoordinator:
    """Orchestrates federated learning across multiple participants."""

    def __init__(self) -> None:
        self._aggregator = FederatedAggregator()
        self._privacy = DifferentialPrivacy()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    async def _load(self, db: AsyncSession, federation_id: str) -> Federation:
        key = _as_uuid(federation_id)
        if key is None:
            raise ValueError(f"Federation {federation_id} not found")

        result = await db.execute(
            select(Federation)
            .options(
                selectinload(Federation.participants),
                selectinload(Federation.rounds),
            )
            .where(Federation.id == key)
            .execution_options(populate_existing=True)
        )
        federation = result.scalar_one_or_none()
        if federation is None:
            raise ValueError(f"Federation {federation_id} not found")
        return federation

    @staticmethod
    def _round_or_raise(federation: Federation, round_id: str) -> FederationRound:
        key = _as_uuid(round_id)
        for rnd in federation.rounds:
            if rnd.id == key:
                return rnd
        raise ValueError(f"Round {round_id} not found")

    # ------------------------------------------------------------------
    # Federation lifecycle
    # ------------------------------------------------------------------

    async def create_federation(
        self,
        db: AsyncSession,
        workspace_id: str,
        name: str,
        model_id: str,
        config: dict | None = None,
    ) -> dict:
        """Create a new federation for collaborative training."""
        merged = {**DEFAULT_CONFIG, **(config or {})}

        federation = Federation(
            id=uuid.uuid4(),
            workspace_id=_as_uuid(workspace_id),
            name=name,
            model_id=model_id,
            status=FederationStatus.waiting,
            aggregation_strategy=merged["aggregation_method"],
            min_participants=merged["min_participants"],
            total_rounds=merged["max_rounds"],
            current_round=0,
            privacy_budget=merged["privacy_budget"],
            privacy_epsilon_spent=0.0,
            config=merged,
        )
        db.add(federation)
        await db.commit()

        return {
            "federation_id": str(federation.id),
            "name": name,
            "status": FederationStatus.waiting.value,
            "config": merged,
        }

    async def join_federation(
        self,
        db: AsyncSession,
        federation_id: str,
        participant_id: str,
        participant_info: dict | None = None,
    ) -> dict:
        """Register a participant in the federation."""
        federation = await self._load(db, federation_id)

        if any(p.site == participant_id for p in federation.participants):
            return {
                "joined": False,
                "participant_count": len(federation.participants),
            }

        info = participant_info or {}
        db.add(
            FederationParticipant(
                id=uuid.uuid4(),
                federation_id=federation.id,
                site=participant_id,
                name=info.get("name", participant_id),
                data_size=int(info.get("data_size", 0)),
                status=ParticipantStatus.connected,
                info=info,
            )
        )

        count = len(federation.participants) + 1
        if (
            federation.status == FederationStatus.waiting
            and count >= federation.min_participants
        ):
            federation.status = FederationStatus.ready

        await db.commit()
        return {"joined": True, "participant_count": count}

    async def start_round(self, db: AsyncSession, federation_id: str) -> dict:
        """Start a new training round — distribute global model to participants."""
        federation = await self._load(db, federation_id)
        config = federation.config or DEFAULT_CONFIG

        min_participants = config.get("min_participants", federation.min_participants)
        if len(federation.participants) < min_participants:
            raise ValueError(
                f"Need at least {min_participants} participants, "
                f"have {len(federation.participants)}"
            )

        max_rounds = config.get("max_rounds", federation.total_rounds)
        if federation.current_round >= max_rounds:
            raise ValueError("Maximum rounds reached")

        if self._privacy.is_budget_exhausted(
            federation.privacy_epsilon_spent, federation.privacy_budget
        ):
            raise ValueError("Privacy budget exhausted")

        federation.current_round += 1
        federation.status = FederationStatus.training
        global_version = f"v{federation.current_round}"

        rnd = FederationRound(
            id=uuid.uuid4(),
            federation_id=federation.id,
            round_number=federation.current_round,
            status=RoundStatus.in_progress,
            global_model_version=global_version,
            participant_count=len(federation.participants),
            updates_received=0,
            updates=[],
            aggregated_metrics={},
            started_at=datetime.now(timezone.utc),
        )
        db.add(rnd)
        await db.commit()

        return {
            "round_id": str(rnd.id),
            "round_number": federation.current_round,
            "global_model_version": global_version,
            "instructions": {
                "action": "train_local_model",
                "min_samples": config.get("min_samples_per_participant", 100),
                "global_weights": federation.global_model,
            },
        }

    async def submit_update(
        self,
        db: AsyncSession,
        federation_id: str,
        round_id: str,
        participant_id: str,
        model_update: dict,
        metrics: dict | None = None,
    ) -> dict:
        """Receive a model update from a participant."""
        federation = await self._load(db, federation_id)
        rnd = self._round_or_raise(federation, round_id)

        submitted = list(rnd.updates or [])
        if any(u["participant_id"] == participant_id for u in submitted):
            raise ValueError("Participant already submitted for this round")

        deserialized = _decode(model_update)

        config = federation.config or DEFAULT_CONFIG
        max_rounds = max(config.get("max_rounds", federation.total_rounds), 1)
        epsilon_per_round = federation.privacy_budget / max_rounds
        noised = self._privacy.add_noise(
            deserialized, epsilon=epsilon_per_round, clip_norm=1.0
        )

        sample_count = (metrics or {}).get("sample_count", 1)
        submitted.append(
            {
                "participant_id": participant_id,
                # Stored encoded: aggregation may run on a different worker.
                "update": _encode(noised),
                "metrics": metrics or {},
                "sample_count": sample_count,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        rnd.updates = submitted
        rnd.updates_received = len(submitted)
        rnd.privacy_epsilon_spent = (
            rnd.privacy_epsilon_spent or 0.0
        ) + epsilon_per_round
        federation.privacy_epsilon_spent += epsilon_per_round

        for participant in federation.participants:
            if participant.site == participant_id:
                participant.samples_contributed += int(sample_count)

        await db.commit()

        return {
            "received": True,
            "updates_so_far": len(submitted),
            "updates_needed": len(federation.participants),
        }

    async def aggregate_round(
        self, db: AsyncSession, federation_id: str, round_id: str
    ) -> dict:
        """Aggregate all participant updates for the round.

        The arithmetic is real: it averages the tensors participants actually
        submitted, weighted by the samples they reported. Nothing here invents
        a metric — a round with no submissions raises rather than producing a
        curve.
        """
        federation = await self._load(db, federation_id)
        rnd = self._round_or_raise(federation, round_id)

        submitted = list(rnd.updates or [])
        if not submitted:
            raise ValueError("No updates to aggregate")

        started = time.perf_counter()
        updates = [_decode(u["update"]) for u in submitted]
        weights = [float(u["sample_count"]) for u in submitted]

        method = (federation.config or {}).get("aggregation_method", "fedavg")
        if method == "fedprox":
            aggregated = self._aggregator.fedprox(
                updates, weights, global_model=_decode(federation.global_model)
            )
        elif method == "trimmed_mean":
            aggregated = self._aggregator.trimmed_mean(updates, weights)
        else:
            aggregated = self._aggregator.fedavg(updates, weights)

        avg_metrics = self._average_metrics(
            [u["metrics"] for u in submitted if u["metrics"]]
        )

        federation.global_model = _encode(aggregated)
        rnd.status = RoundStatus.completed
        rnd.aggregated_metrics = avg_metrics
        rnd.finished_at = datetime.now(timezone.utc)
        rnd.aggregation_time_ms = round((time.perf_counter() - started) * 1000, 3)

        contributors = {u["participant_id"] for u in submitted}
        for participant in federation.participants:
            if participant.site in contributors:
                participant.rounds_contributed += 1

        await db.commit()

        return {
            "new_global_version": f"v{federation.current_round}-aggregated",
            "participants": len(submitted),
            "avg_metrics": avg_metrics,
            "round_complete": True,
        }

    async def get_federation_status(
        self, db: AsyncSession, federation_id: str
    ) -> dict:
        """Return current federation status."""
        federation = await self._load(db, federation_id)

        history = [
            {
                "round": r.round_number,
                "metrics": r.aggregated_metrics or {},
                "participants": r.updates_received,
            }
            for r in sorted(federation.rounds, key=lambda r: r.round_number)
            if r.status == RoundStatus.completed
        ]

        return {
            "status": federation.status.value,
            "current_round": federation.current_round,
            "participants": [
                {"id": p.site, "status": p.status.value}
                for p in federation.participants
            ],
            "metrics_history": history,
        }

    async def stop_federation(self, db: AsyncSession, federation_id: str) -> dict:
        """Stop the federation and return final results."""
        federation = await self._load(db, federation_id)
        federation.status = FederationStatus.stopped

        completed = [
            r
            for r in sorted(federation.rounds, key=lambda r: r.round_number)
            if r.status == RoundStatus.completed
        ]
        final_metrics = completed[-1].aggregated_metrics if completed else {}

        await db.commit()
        return {
            "stopped": True,
            "total_rounds": federation.current_round,
            "final_metrics": final_metrics or {},
        }

    async def list_rounds(self, db: AsyncSession, federation_id: str) -> list[dict]:
        """Return the rounds that actually ran, oldest first."""
        federation = await self._load(db, federation_id)

        return [
            {
                "round": r.round_number,
                "status": r.status.value,
                "participants": r.updates_received,
                "metrics": r.aggregated_metrics or {},
                "privacy_epsilon_spent": round(r.privacy_epsilon_spent or 0.0, 6),
                "started_at": _iso(r.started_at),
                "completed_at": _iso(r.finished_at),
                "aggregation_time_ms": r.aggregation_time_ms,
            }
            for r in sorted(federation.rounds, key=lambda r: r.round_number)
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_model(model: dict | None) -> dict | None:
        return _encode(model)

    @staticmethod
    def _deserialize_update(model_update: dict) -> dict:
        return _decode(model_update)

    @staticmethod
    def _average_metrics(metrics_list: list[dict]) -> dict:
        if not metrics_list:
            return {}
        keys: set[str] = set()
        for m in metrics_list:
            keys.update(m.keys())
        avg: dict[str, float] = {}
        for k in keys:
            vals = [
                m[k] for m in metrics_list if k in m and isinstance(m[k], (int, float))
            ]
            if vals:
                avg[k] = sum(vals) / len(vals)
        return avg
