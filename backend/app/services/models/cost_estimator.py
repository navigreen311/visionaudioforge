"""Training and inference cost estimation service."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# GPU instance catalog: (name, TFLOPS_fp32, VRAM_GB, cost_per_hour_usd)
_GPU_CATALOG = {
    "T4": {"tflops": 8.1, "vram_gb": 16, "cost_per_hour": 0.50},
    "A10G": {"tflops": 31.2, "vram_gb": 24, "cost_per_hour": 1.00},
    "A100": {"tflops": 156.0, "vram_gb": 80, "cost_per_hour": 2.50},
}

# Rough throughput: samples/sec ≈ tflops * 1e12 / (model_params * 6)
# (6 FLOPs per param per sample for fwd+bwd)
_FLOPS_PER_PARAM_PER_SAMPLE = 6


class TrainingCostEstimator:
    """Estimate training time, GPU hours, and dollar cost for fine-tuning jobs."""

    def estimate_cost(self, config: dict[str, Any]) -> dict[str, Any]:
        """Estimate training cost from a configuration dict.

        Expected keys in *config*:
            model_params (int): Total model parameters.
            num_epochs (int): Number of training epochs.
            num_samples (int): Training-set size.
            gpu_type (str): One of "T4", "A10G", "A100". Defaults to "T4".
        """
        model_params = config.get("model_params", 11_000_000)  # ~resnet18
        num_epochs = config.get("num_epochs", 10)
        num_samples = config.get("num_samples", 10_000)
        gpu_type = config.get("gpu_type", "T4")

        gpu = _GPU_CATALOG.get(gpu_type, _GPU_CATALOG["T4"])
        tflops = gpu["tflops"]
        cost_per_hour = gpu["cost_per_hour"]

        # Throughput estimate
        flops_per_sample = model_params * _FLOPS_PER_PARAM_PER_SAMPLE
        throughput = (tflops * 1e12) / flops_per_sample  # samples/sec

        total_samples = num_epochs * num_samples
        estimated_seconds = total_samples / throughput if throughput > 0 else 0
        estimated_minutes = estimated_seconds / 60
        estimated_gpu_hours = estimated_seconds / 3600
        estimated_cost_usd = estimated_gpu_hours * cost_per_hour

        return {
            "estimated_time_minutes": round(estimated_minutes, 2),
            "estimated_gpu_hours": round(estimated_gpu_hours, 4),
            "estimated_cost_usd": round(estimated_cost_usd, 4),
            "breakdown": {
                "model_params": model_params,
                "num_epochs": num_epochs,
                "num_samples": num_samples,
                "gpu_type": gpu_type,
                "throughput_samples_per_sec": round(throughput, 1),
                "cost_per_gpu_hour": cost_per_hour,
            },
        }

    def estimate_inference_cost(
        self, model_params: int, requests_per_day: int
    ) -> dict[str, float]:
        """Estimate per-request and daily/monthly inference cost.

        Assumes a T4 instance running continuously at ~$0.50/hr and a simple
        throughput model.
        """
        gpu = _GPU_CATALOG["T4"]
        flops_per_request = model_params * 2  # forward only ≈ 2 FLOPs/param
        throughput = (gpu["tflops"] * 1e12) / flops_per_request  # req/sec

        seconds_per_day = requests_per_day / throughput if throughput > 0 else 0
        gpu_hours_per_day = seconds_per_day / 3600
        daily_cost = gpu_hours_per_day * gpu["cost_per_hour"]
        cost_per_request = daily_cost / requests_per_day if requests_per_day > 0 else 0

        return {
            "cost_per_request": round(cost_per_request, 8),
            "daily_cost": round(daily_cost, 4),
            "monthly_cost": round(daily_cost * 30, 4),
        }

    def recommend_instance(
        self, model_params: int, batch_size: int = 32
    ) -> dict[str, Any]:
        """Recommend a GPU instance based on model size and batch size.

        Heuristic: model memory ≈ params * 4 bytes (fp32) * 3 (gradients +
        optimizer state). Pick the cheapest GPU whose VRAM fits.
        """
        estimated_memory_gb = (model_params * 4 * 3) / (1024**3)
        # Add batch memory estimate (rough: batch_size * model_params * 4 / 1e9)
        batch_memory_gb = (batch_size * model_params * 4) / (1024**3)
        total_memory_gb = estimated_memory_gb + batch_memory_gb

        ranked = sorted(_GPU_CATALOG.items(), key=lambda x: x[1]["cost_per_hour"])
        recommended = None
        alternatives = []

        for name, spec in ranked:
            entry = {
                "name": name,
                "vram_gb": spec["vram_gb"],
                "cost_per_hour": spec["cost_per_hour"],
            }
            if spec["vram_gb"] >= total_memory_gb:
                if recommended is None:
                    recommended = entry
                else:
                    alternatives.append(entry)
            else:
                alternatives.append(entry)

        if recommended is None:
            recommended = {
                "name": "A100",
                "vram_gb": 80,
                "cost_per_hour": 2.50,
            }

        return {
            "recommended": recommended,
            "alternatives": alternatives,
            "estimated_memory_gb": round(total_memory_gb, 2),
        }
