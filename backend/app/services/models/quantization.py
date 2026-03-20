"""Model quantization service for size reduction and inference speed-up."""

import logging
import time
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# Bytes per parameter for each dtype
_BYTES_PER_PARAM = {
    "float32": 4,
    "float16": 2,
    "int8": 1,
}


class ModelQuantizer:
    """Utilities for dynamic/static quantization, size estimation, and benchmarking."""

    def quantize_dynamic(
        self, model: nn.Module, dtype: str = "int8"
    ) -> nn.Module:
        """Apply PyTorch dynamic quantization to all Linear layers.

        Args:
            model: The model to quantize.
            dtype: Target dtype — ``"int8"`` (qint8) or ``"float16"`` (float16).

        Returns:
            The dynamically-quantized model (CPU only).
        """
        model = model.cpu()

        if dtype == "float16":
            qt = torch.float16
        else:
            qt = torch.qint8

        quantized = torch.quantization.quantize_dynamic(
            model,
            {nn.Linear},
            dtype=qt,
        )
        logger.info("Dynamic quantization applied (dtype=%s)", dtype)
        return quantized

    def quantize_static_stub(
        self,
        model: nn.Module,
        calibration_data: Any | None = None,
    ) -> dict[str, Any]:
        """Stub for static quantization — requires calibration data.

        Static quantization is more involved than dynamic: it needs a
        representative calibration dataset to determine activation ranges.
        This stub returns guidance without performing the actual quantization.
        """
        return {
            "status": "stub",
            "note": (
                "Static quantization requires calibration data to determine "
                "activation ranges. Provide a representative DataLoader via "
                "the calibration_data parameter. A future version will run "
                "the full prepare → calibrate → convert pipeline."
            ),
            "calibration_data_provided": calibration_data is not None,
        }

    def estimate_size_reduction(
        self,
        original_params: int,
        dtype: str = "int8",
    ) -> dict[str, float]:
        """Estimate model size before and after quantization.

        Assumes the original model uses float32 (4 bytes / param).
        """
        original_bytes = original_params * _BYTES_PER_PARAM["float32"]
        target_bytes_per_param = _BYTES_PER_PARAM.get(dtype, 1)
        quantized_bytes = original_params * target_bytes_per_param

        original_mb = original_bytes / (1024 * 1024)
        quantized_mb = quantized_bytes / (1024 * 1024)
        reduction_pct = (
            (1 - quantized_mb / original_mb) * 100 if original_mb > 0 else 0.0
        )

        return {
            "original_mb": round(original_mb, 2),
            "quantized_mb": round(quantized_mb, 2),
            "reduction_pct": round(reduction_pct, 2),
        }

    def compare_inference_speed(
        self,
        model: nn.Module,
        quantized_model: nn.Module,
        sample_input: torch.Tensor,
    ) -> dict[str, float]:
        """Time a forward pass on both models and return speed-up ratio.

        Both models are run on CPU for a fair comparison.
        """
        sample_input = sample_input.cpu()

        # Warm-up
        with torch.no_grad():
            model.cpu()(sample_input)
            quantized_model.cpu()(sample_input)

        # Time original
        n_runs = 5
        start = time.perf_counter()
        with torch.no_grad():
            for _ in range(n_runs):
                model(sample_input)
        original_ms = (time.perf_counter() - start) / n_runs * 1000

        # Time quantized
        start = time.perf_counter()
        with torch.no_grad():
            for _ in range(n_runs):
                quantized_model(sample_input)
        quantized_ms = (time.perf_counter() - start) / n_runs * 1000

        speedup = original_ms / quantized_ms if quantized_ms > 0 else 0.0

        return {
            "original_ms": round(original_ms, 3),
            "quantized_ms": round(quantized_ms, 3),
            "speedup": round(speedup, 3),
        }
