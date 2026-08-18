"""ONNX model export, optimization, validation, and benchmarking."""

from __future__ import annotations

import inspect
import os
import time
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    import torch.nn as nn

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import onnx
    import onnx.checker

    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    import onnxoptimizer  # type: ignore[import-untyped]

    HAS_ONNX_OPTIMIZER = True
except ImportError:
    HAS_ONNX_OPTIMIZER = False

try:
    import onnxruntime as ort  # type: ignore[import-untyped]

    HAS_ORT = True
except ImportError:
    HAS_ORT = False


class ONNXExporter:
    """Export PyTorch models to ONNX and run optimization / validation / benchmarks."""

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_to_onnx(
        self,
        model: Any,
        input_shape: tuple[int, ...],
        output_path: str,
        opset_version: int = 13,
    ) -> dict:
        """Export a PyTorch ``nn.Module`` (or traced model) to ONNX.

        Returns metadata about the exported file.
        """
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is required for ONNX export. Install: pip install torch")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Prepare model
        if isinstance(model, nn.Module):
            model.eval()

        dummy_input = torch.randn(*input_shape)

        input_names = ["input"]
        output_names = ["output"]

        export_kwargs = {
            "opset_version": opset_version,
            "input_names": input_names,
            "output_names": output_names,
            "dynamic_axes": {
                "input": {0: "batch_size"},
                "output": {0: "batch_size"},
            },
        }

        # torch 2.9 switched torch.onnx.export to the dynamo exporter by
        # default, which needs the separate onnxscript package. Ask for the
        # legacy tracer explicitly where the argument exists, so export works
        # on both the pinned torch and newer ones without a new dependency.
        if "dynamo" in inspect.signature(torch.onnx.export).parameters:
            export_kwargs["dynamo"] = False

        torch.onnx.export(model, dummy_input, output_path, **export_kwargs)

        # Validate if onnx is available
        if HAS_ONNX:
            onnx_model = onnx.load(output_path)
            onnx.checker.check_model(onnx_model)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        return {
            "path": output_path,
            "size_mb": round(size_mb, 4),
            "opset": opset_version,
            "input_names": input_names,
            "output_names": output_names,
        }

    # ------------------------------------------------------------------
    # Optimize
    # ------------------------------------------------------------------

    def optimize_onnx(
        self,
        onnx_path: str,
        output_path: str | None = None,
    ) -> dict:
        """Optimize an ONNX model — constant folding, redundant-node removal, fusions.

        Falls back to a copy when ``onnxoptimizer`` is not installed.
        """
        if not HAS_ONNX:
            raise RuntimeError("onnx package is required. Install: pip install onnx")

        original_size = os.path.getsize(onnx_path) / (1024 * 1024)

        if output_path is None:
            stem = Path(onnx_path).stem
            output_path = str(Path(onnx_path).parent / f"{stem}_optimized.onnx")

        model = onnx.load(onnx_path)

        if HAS_ONNX_OPTIMIZER:
            passes = [
                "eliminate_identity",
                "eliminate_nop_transpose",
                "eliminate_nop_pad",
                "eliminate_unused_initializer",
                "fuse_consecutive_transposes",
                "fuse_transpose_into_gemm",
                "fuse_bn_into_conv",
            ]
            model = onnxoptimizer.optimize(model, passes)

        onnx.save(model, output_path)
        optimized_size = os.path.getsize(output_path) / (1024 * 1024)

        reduction = (
            ((original_size - optimized_size) / original_size * 100)
            if original_size > 0
            else 0.0
        )

        return {
            "path": output_path,
            "original_size_mb": round(original_size, 4),
            "optimized_size_mb": round(optimized_size, 4),
            "reduction_pct": round(reduction, 2),
        }

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate_onnx(self, onnx_path: str) -> dict:
        """Validate an ONNX model and return structural info."""
        if not HAS_ONNX:
            raise RuntimeError("onnx package is required. Install: pip install onnx")

        model = onnx.load(onnx_path)

        valid = True
        try:
            onnx.checker.check_model(model)
        except onnx.checker.ValidationError:
            valid = False

        inputs = [
            {
                "name": inp.name,
                "shape": [
                    d.dim_value if d.dim_value else d.dim_param
                    for d in inp.type.tensor_type.shape.dim
                ],
                "dtype": inp.type.tensor_type.elem_type,
            }
            for inp in model.graph.input
        ]

        outputs = [
            {
                "name": out.name,
                "shape": [
                    d.dim_value if d.dim_value else d.dim_param
                    for d in out.type.tensor_type.shape.dim
                ],
                "dtype": out.type.tensor_type.elem_type,
            }
            for out in model.graph.output
        ]

        return {
            "valid": valid,
            "inputs": inputs,
            "outputs": outputs,
            "node_count": len(model.graph.node),
            "opset": model.opset_import[0].version if model.opset_import else 0,
        }

    # ------------------------------------------------------------------
    # Benchmark
    # ------------------------------------------------------------------

    def benchmark_onnx(
        self,
        onnx_path: str,
        input_data: np.ndarray | None = None,
        iterations: int = 100,
    ) -> dict:
        """Benchmark ONNX model inference latency.

        Uses ``onnxruntime`` when available; otherwise returns an estimate
        derived from the node count.
        """
        if HAS_ORT:
            sess = ort.InferenceSession(onnx_path)
            input_name = sess.get_inputs()[0].name

            if input_data is None:
                shape = [
                    d if isinstance(d, int) and d > 0 else 1
                    for d in sess.get_inputs()[0].shape
                ]
                input_data = np.random.randn(*shape).astype(np.float32)

            # Warm-up
            for _ in range(min(5, iterations)):
                sess.run(None, {input_name: input_data})

            latencies: list[float] = []
            for _ in range(iterations):
                t0 = time.perf_counter()
                sess.run(None, {input_name: input_data})
                latencies.append((time.perf_counter() - t0) * 1000)

            latencies.sort()
            avg_ms = sum(latencies) / len(latencies)
            p95_ms = latencies[int(len(latencies) * 0.95)]
            throughput = 1000.0 / avg_ms if avg_ms > 0 else 0.0

            return {
                "avg_ms": round(avg_ms, 3),
                "p95_ms": round(p95_ms, 3),
                "throughput_per_s": round(throughput, 2),
            }

        # Fallback: estimate from node count
        if HAS_ONNX:
            model = onnx.load(onnx_path)
            node_count = len(model.graph.node)
        else:
            node_count = 100  # default guess

        estimated_ms = node_count * 0.05  # rough heuristic
        return {
            "avg_ms": round(estimated_ms, 3),
            "p95_ms": round(estimated_ms * 1.2, 3),
            "throughput_per_s": round(1000.0 / estimated_ms if estimated_ms > 0 else 0, 2),
        }
