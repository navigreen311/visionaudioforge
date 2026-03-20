"""GPU Scheduler — device status, memory estimation, and job scheduling."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Bytes per parameter for each dtype
_DTYPE_BYTES: dict[str, int] = {
    "float32": 4,
    "float16": 2,
    "bfloat16": 2,
    "int8": 1,
}


@dataclass
class _Job:
    job_id: str
    model_params: int
    priority: str
    submitted_at: float = field(default_factory=time.time)


class GPUScheduler:
    """Manage GPU resources and schedule inference jobs."""

    def __init__(self) -> None:
        self._queue: list[_Job] = []

    # ------------------------------------------------------------------
    # GPU status
    # ------------------------------------------------------------------

    def get_gpu_status(self) -> list[dict[str, Any]]:
        """Return per-device GPU information.

        V1: attempt ``torch.cuda``; fall back to stub data when CUDA is
        unavailable.
        """
        try:
            import torch

            if not torch.cuda.is_available():
                raise RuntimeError("CUDA not available")

            devices: list[dict[str, Any]] = []
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                mem_total = props.total_mem // (1024 * 1024)
                mem_used = torch.cuda.memory_allocated(i) // (1024 * 1024)
                utilization = (mem_used / mem_total * 100) if mem_total else 0.0
                devices.append(
                    {
                        "device_id": i,
                        "name": props.name,
                        "memory_total_mb": mem_total,
                        "memory_used_mb": mem_used,
                        "utilization_pct": round(utilization, 1),
                        "temperature_c": 0.0,  # not available via torch
                    }
                )
            return devices
        except Exception:
            return [
                {
                    "device_id": 0,
                    "name": "CPU",
                    "memory_total_mb": 0,
                    "memory_used_mb": 0,
                    "utilization_pct": 0.0,
                    "temperature_c": 0.0,
                    "note": "No GPU available",
                }
            ]

    # ------------------------------------------------------------------
    # Memory estimation
    # ------------------------------------------------------------------

    def estimate_memory(
        self,
        model_params: int,
        batch_size: int = 1,
        dtype: str = "float32",
    ) -> dict[str, float]:
        """Estimate GPU memory required for a model.

        Returns ``{"estimated_mb": float}``.
        """
        bytes_per_param = _DTYPE_BYTES.get(dtype, 4)
        param_bytes = model_params * bytes_per_param
        # Activations estimate: roughly proportional to batch size
        activation_bytes = param_bytes * batch_size
        total_bytes = param_bytes + activation_bytes
        estimated_mb = total_bytes / (1024 * 1024)
        return {"estimated_mb": round(estimated_mb, 2)}

    def can_fit_model(
        self,
        model_params: int,
        device_id: int = 0,
        dtype: str = "float32",
    ) -> dict[str, Any]:
        """Check whether a model fits on the specified device."""
        status = self.get_gpu_status()
        device = None
        for d in status:
            if d["device_id"] == device_id:
                device = d
                break

        if device is None:
            return {"fits": False, "available_mb": 0.0, "required_mb": 0.0}

        required = self.estimate_memory(model_params, batch_size=1, dtype=dtype)["estimated_mb"]
        available = device["memory_total_mb"] - device.get("memory_used_mb", 0)

        return {
            "fits": available >= required,
            "available_mb": float(available),
            "required_mb": required,
        }

    # ------------------------------------------------------------------
    # Job scheduling (V1: simple priority FIFO queue)
    # ------------------------------------------------------------------

    def schedule_job(
        self,
        job_id: str,
        model_params: int,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Enqueue a job. Higher priority jobs jump the queue."""
        job = _Job(job_id=job_id, model_params=model_params, priority=priority)

        if priority == "high":
            # Insert before first normal/low job
            insert_idx = 0
            for i, existing in enumerate(self._queue):
                if existing.priority == "high":
                    insert_idx = i + 1
                else:
                    break
            self._queue.insert(insert_idx, job)
        else:
            self._queue.append(job)

        position = self._queue.index(job)
        estimated_wait = position * 2.0  # rough 2s per job estimate

        return {
            "device_id": 0,
            "estimated_wait_s": estimated_wait,
            "position_in_queue": position,
        }

    def get_queue(self) -> list[dict[str, Any]]:
        """Return current job queue snapshot."""
        return [
            {
                "job_id": j.job_id,
                "model_params": j.model_params,
                "priority": j.priority,
                "submitted_at": j.submitted_at,
            }
            for j in self._queue
        ]

    # ------------------------------------------------------------------
    # Loading strategy
    # ------------------------------------------------------------------

    def model_loading_strategy(
        self,
        model_params: int,
        access_frequency: float,
    ) -> dict[str, str]:
        """Decide hot / warm / cold loading strategy.

        ``access_frequency`` is requests per hour.
        """
        if access_frequency > 10:
            return {
                "strategy": "hot",
                "reason": f"High access frequency ({access_frequency}/hr) — keep always in memory",
            }
        elif access_frequency > 1:
            return {
                "strategy": "warm",
                "reason": f"Moderate access ({access_frequency}/hr) — load on first request, keep 5 min",
            }
        else:
            return {
                "strategy": "cold",
                "reason": f"Low access ({access_frequency}/hr) — load on demand, unload immediately",
            }
