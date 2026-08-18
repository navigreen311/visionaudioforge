"""Export pipeline — orchestrates ONNX export, format conversion, and
edge-deployment packaging."""

from __future__ import annotations

import json
import os
import tempfile
import textwrap
import uuid
from pathlib import Path
from typing import Any

from app.services.edge.onnx_export import ONNXExporter
from app.services.edge.converters import ModelConverter

try:
    import torch
    import torch.nn as nn

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# Export and package records live in model_exports / offline_packages. The
# artefacts these produce sit on disk and in object storage; when the record of
# them was a module-level dict, a restart left the files present with nothing
# pointing at them and the job reporting "not_found".
#
# The exporter still takes an optional session: the pure-conversion paths are
# used directly in tests without a database, and are not worth forcing a
# connection on.


def _uuid_or_none(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def _save_export(db, workspace_id, record: dict) -> dict:
    """Persist an export record, returning it with its stored id."""
    if db is None:
        return record

    from app.models.edge_export import ModelExport

    row = ModelExport(
        workspace_id=_uuid_or_none(workspace_id),
        model_id=str(record.get("model_id", "")),
        format=",".join(record.get("formats", [])) or "onnx",
        status=record.get("status", "completed"),
        file_size_mb=record.get("total_size_mb"),
        details=record,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    record["export_id"] = str(row.id)
    return record


async def _load_export(db, export_id: str) -> dict | None:
    if db is None:
        return None

    from sqlalchemy import select

    from app.models.edge_export import ModelExport

    eid = _uuid_or_none(export_id)
    if eid is None:
        return None
    row = (
        await db.execute(select(ModelExport).where(ModelExport.id == eid))
    ).scalar_one_or_none()
    return dict(row.details or {}, export_id=str(row.id)) if row else None


class ExportPipeline:
    """High-level pipeline for exporting models to edge formats."""

    def __init__(self) -> None:
        self._onnx = ONNXExporter()
        self._converter = ModelConverter()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_model(
        self,
        db: Any,
        model_id: str,
        formats: list[str],
        optimization_level: str = "basic",
        workspace_id: str | None = None,
    ) -> dict:
        """Export a model to one or more formats.

        For ``onnx`` a real export is performed using a placeholder model.
        For other formats, stub results with installation instructions are returned.

        ``optimization_level``: ``'none'``, ``'basic'`` (constant folding),
        ``'aggressive'`` (quantize + prune).
        """
        supported = {"onnx", "tensorrt", "openvino", "coreml", "tflite", "webgpu"}
        invalid = set(formats) - supported
        if invalid:
            raise ValueError(f"Unsupported formats: {invalid}")

        export_id = str(uuid.uuid4())
        exports: dict[str, Any] = {}
        total_size = 0.0

        # Build a simple placeholder model when needed
        onnx_path: str | None = None

        if "onnx" in formats:
            if not HAS_TORCH:
                exports["onnx"] = {
                    "status": "error",
                    "note": "PyTorch not installed. Install: pip install torch",
                }
            else:
                model = nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 5))
                out_dir = Path(tempfile.mkdtemp()) / "exports"
                out_dir.mkdir(parents=True, exist_ok=True)
                onnx_path = str(out_dir / f"{model_id}.onnx")

                result = self._onnx.export_to_onnx(
                    model, (1, 10), onnx_path, opset_version=13
                )

                if optimization_level in ("basic", "aggressive"):
                    opt_result = self._onnx.optimize_onnx(onnx_path)
                    result["optimization"] = opt_result

                exports["onnx"] = result
                total_size += result["size_mb"]

        # Stub formats
        stub_map = {
            "tensorrt": self._converter.to_tensorrt_stub,
            "openvino": self._converter.to_openvino_stub,
            "coreml": self._converter.to_coreml_stub,
            "tflite": self._converter.to_tflite_stub,
            "webgpu": self._converter.to_webgpu_stub,
        }

        source = onnx_path or "model.onnx"
        for fmt in formats:
            if fmt != "onnx" and fmt in stub_map:
                exports[fmt] = stub_map[fmt](source)

        record = {
            "export_id": export_id,
            "model_id": model_id,
            "formats": formats,
            "optimization_level": optimization_level,
            "exports": exports,
            "total_size_mb": round(total_size, 4),
            "status": "completed",
        }
        return await _save_export(db, workspace_id, record)

    # ------------------------------------------------------------------
    # Status / listing
    # ------------------------------------------------------------------

    async def get_export_status(self, export_id: str, db: Any = None) -> dict:
        record = await _load_export(db, export_id)
        if record is None:
            return {"export_id": export_id, "status": "not_found"}
        return record

    async def list_exports(self, db: Any, workspace_id: str) -> list[dict]:
        if db is None:
            return []

        from sqlalchemy import select

        from app.models.edge_export import ModelExport

        stmt = select(ModelExport)
        ws = _uuid_or_none(workspace_id)
        if ws is not None:
            stmt = stmt.where(ModelExport.workspace_id == ws)
        rows = (await db.execute(stmt.order_by(ModelExport.created_at))).scalars().all()
        return [dict(r.details or {}, export_id=str(r.id)) for r in rows]

    async def download_export(self, export_id: str, fmt: str, db: Any = None) -> str:
        record = await _load_export(db, export_id)
        if not record:
            raise FileNotFoundError(f"Export {export_id} not found")
        fmt_data = record["exports"].get(fmt, {})
        path = fmt_data.get("path")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"No downloadable file for format '{fmt}'")
        return path

    # ------------------------------------------------------------------
    # Edge package
    # ------------------------------------------------------------------

    async def create_edge_package(
        self,
        db: Any,
        model_id: str,
        fmt: str,
        config: dict | None = None,
        workspace_id: str | None = None,
    ) -> dict:
        """Create a deployable edge package: model + config + requirements + sample code."""
        package_id = str(uuid.uuid4())
        pkg_dir = Path(tempfile.mkdtemp()) / f"edge_package_{package_id}"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Config
        model_config = config or {
            "model_id": model_id,
            "format": fmt,
            "input_shape": [1, 10],
            "output_shape": [1, 5],
            "preprocessing": {"normalize": True, "mean": [0.485], "std": [0.229]},
        }
        (pkg_dir / "config.json").write_text(json.dumps(model_config, indent=2))

        # Requirements
        requirements = self._requirements_for_format(fmt)
        (pkg_dir / "requirements.txt").write_text(requirements)

        # Sample inference code
        inference_code = await self.generate_inference_code(fmt, model_config)
        (pkg_dir / "inference.py").write_text(inference_code)

        includes = ["config.json", "requirements.txt", "inference.py"]

        # If ONNX, also export a model file into the package
        size_mb = 0.0
        if fmt == "onnx" and HAS_TORCH:
            model = nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 5))
            model_path = str(pkg_dir / "model.onnx")
            self._onnx.export_to_onnx(model, (1, 10), model_path)
            includes.append("model.onnx")
            size_mb = os.path.getsize(model_path) / (1024 * 1024)

        record = {
            "package_id": package_id,
            "format": fmt,
            "size_mb": round(size_mb, 4),
            "includes": includes,
            "path": str(pkg_dir),
        }
        if db is not None:
            from app.models.edge_fleet import OfflinePackage

            row = OfflinePackage(
                workspace_id=_uuid_or_none(workspace_id),
                model_id=str(model_id or ""),
                device_type=str((config or {}).get("target", "")),
                model_format=fmt,
                size_mb=round(size_mb, 4),
                contents=includes,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            record["package_id"] = str(row.id)

        return record

    # ------------------------------------------------------------------
    # Inference code generation
    # ------------------------------------------------------------------

    async def generate_inference_code(self, fmt: str, model_info: dict) -> str:
        """Generate sample Python inference code for a given format."""
        generators = {
            "onnx": self._gen_onnx_code,
            "tensorrt": self._gen_tensorrt_code,
            "openvino": self._gen_openvino_code,
            "coreml": self._gen_coreml_code,
            "tflite": self._gen_tflite_code,
            "webgpu": self._gen_webgpu_code,
        }
        gen = generators.get(fmt, self._gen_onnx_code)
        return gen(model_info)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _requirements_for_format(fmt: str) -> str:
        reqs = {
            "onnx": "onnx>=1.14\nonnxruntime>=1.15\nnumpy",
            "tensorrt": "tensorrt>=8.6\nnumpy\npycuda",
            "openvino": "openvino>=2023.0\nnumpy",
            "coreml": "coremltools>=6.0\nnumpy",
            "tflite": "tensorflow>=2.13\nnumpy",
            "webgpu": "# Browser-based — no Python deps\nonnx>=1.14",
        }
        return reqs.get(fmt, "numpy")

    @staticmethod
    def _gen_onnx_code(info: dict) -> str:
        return textwrap.dedent("""\
            \"\"\"ONNX Runtime inference example.\"\"\"
            import numpy as np
            import onnxruntime as ort

            session = ort.InferenceSession("model.onnx")
            input_name = session.get_inputs()[0].name
            input_shape = {input_shape}

            # Prepare input
            input_data = np.random.randn(*input_shape).astype(np.float32)

            # Run inference
            outputs = session.run(None, {{input_name: input_data}})
            print("Output shape:", outputs[0].shape)
            print("Output:", outputs[0])
        """).format(input_shape=info.get("input_shape", [1, 10]))

    @staticmethod
    def _gen_tensorrt_code(info: dict) -> str:
        return textwrap.dedent("""\
            \"\"\"TensorRT inference example.\"\"\"
            import numpy as np
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit

            # Load TensorRT engine
            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
            with open("model.trt", "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
                engine = runtime.deserialize_cuda_engine(f.read())

            context = engine.create_execution_context()
            # Allocate buffers and run inference (see TensorRT docs)
            print("TensorRT engine loaded successfully")
        """)

    @staticmethod
    def _gen_openvino_code(info: dict) -> str:
        return textwrap.dedent("""\
            \"\"\"OpenVINO inference example.\"\"\"
            import numpy as np
            from openvino.runtime import Core

            core = Core()
            model = core.read_model("model.xml")
            compiled = core.compile_model(model, "CPU")
            input_shape = {input_shape}

            input_data = np.random.randn(*input_shape).astype(np.float32)
            result = compiled([input_data])
            print("Output:", result[0])
        """).format(input_shape=info.get("input_shape", [1, 10]))

    @staticmethod
    def _gen_coreml_code(info: dict) -> str:
        return textwrap.dedent("""\
            \"\"\"CoreML inference example.\"\"\"
            import coremltools as ct
            import numpy as np

            model = ct.models.MLModel("model.mlmodel")
            input_data = np.random.randn(*{input_shape}).astype(np.float32)
            prediction = model.predict({{"input": input_data}})
            print("Prediction:", prediction)
        """).format(input_shape=info.get("input_shape", [1, 10]))

    @staticmethod
    def _gen_tflite_code(info: dict) -> str:
        return textwrap.dedent("""\
            \"\"\"TFLite inference example.\"\"\"
            import numpy as np
            import tensorflow as tf

            interpreter = tf.lite.Interpreter(model_path="model.tflite")
            interpreter.allocate_tensors()

            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            input_shape = input_details[0]["shape"]
            input_data = np.random.randn(*input_shape).astype(np.float32)
            interpreter.set_tensor(input_details[0]["index"], input_data)
            interpreter.invoke()

            output = interpreter.get_tensor(output_details[0]["index"])
            print("Output:", output)
        """)

    @staticmethod
    def _gen_webgpu_code(info: dict) -> str:
        return textwrap.dedent("""\
            // WebGPU inference example (JavaScript / browser)
            // Include ONNX Runtime Web: <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js"></script>

            async function runInference() {
                const session = await ort.InferenceSession.create("model.onnx", {
                    executionProviders: ["webgpu"],
                });

                const inputShape = %s;
                const inputData = new Float32Array(inputShape.reduce((a, b) => a * b, 1));
                // Fill inputData with your values

                const tensor = new ort.Tensor("float32", inputData, inputShape);
                const feeds = { input: tensor };
                const results = await session.run(feeds);
                console.log("Output:", results.output.data);
            }

            runInference();
        """) % info.get("input_shape", [1, 10])
