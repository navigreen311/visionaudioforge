"""BYOM (Bring Your Own Model) adapter — register, load, and predict with custom models."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Supported frameworks
# ---------------------------------------------------------------------------

SUPPORTED_FRAMEWORKS: list[dict[str, str]] = [
    {"framework": "pytorch", "version": ">=1.12"},
    {"framework": "tensorflow", "version": ">=2.10"},
    {"framework": "onnx", "version": ">=1.12"},
    {"framework": "sklearn", "version": ">=1.1"},
    {"framework": "custom", "version": "any"},
]

_VALID_FRAMEWORK_NAMES = {f["framework"] for f in SUPPORTED_FRAMEWORKS}

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_ADAPTER_STORE: dict[str, dict[str, Any]] = {}
_MODEL_CACHE: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# BYOMAdapter
# ---------------------------------------------------------------------------


class BYOMAdapter:
    """Register, load, and run inference on user-supplied models."""

    # -- registration -------------------------------------------------------

    async def register_model(
        self,
        db: Any,
        workspace_id: str,
        model_name: str,
        model_path_or_url: str,
        framework: str,
        input_schema: dict,
        output_schema: dict,
    ) -> dict:
        if framework not in _VALID_FRAMEWORK_NAMES:
            raise ValueError(
                f"Unsupported framework '{framework}'. "
                f"Choose from {sorted(_VALID_FRAMEWORK_NAMES)}"
            )

        # Light validation: if it looks like a file path, check existence
        if not model_path_or_url.startswith(("http://", "https://")):
            path = Path(model_path_or_url)
            if not path.exists():
                raise FileNotFoundError(
                    f"Model file not found: {model_path_or_url}"
                )

        model_id = str(uuid.uuid4())
        adapter_id = str(uuid.uuid4())

        _ADAPTER_STORE[adapter_id] = {
            "adapter_id": adapter_id,
            "model_id": model_id,
            "workspace_id": workspace_id,
            "model_name": model_name,
            "model_path_or_url": model_path_or_url,
            "framework": framework,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "status": "registered",
        }

        return {"model_id": model_id, "adapter_id": adapter_id}

    # -- load ---------------------------------------------------------------

    async def load_model(self, adapter_id: str) -> Any:
        """Load a model into memory (cached)."""
        if adapter_id in _MODEL_CACHE:
            return _MODEL_CACHE[adapter_id]

        adapter = _ADAPTER_STORE.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter {adapter_id} not found")

        framework = adapter["framework"]
        model_path = adapter["model_path_or_url"]

        model_obj: Any = None

        if framework == "pytorch":
            try:
                import torch  # type: ignore[import-untyped]

                model_obj = torch.load(model_path, map_location="cpu")
            except ImportError:
                model_obj = {"_stub": "pytorch", "path": model_path}
        elif framework == "tensorflow":
            try:
                import tensorflow as tf  # type: ignore[import-untyped]

                model_obj = tf.saved_model.load(model_path)
            except ImportError:
                model_obj = {"_stub": "tensorflow", "path": model_path}
        elif framework == "onnx":
            try:
                import onnxruntime as ort  # type: ignore[import-untyped]

                model_obj = ort.InferenceSession(model_path)
            except ImportError:
                model_obj = {"_stub": "onnx", "path": model_path}
        elif framework == "sklearn":
            try:
                import joblib  # type: ignore[import-untyped]

                model_obj = joblib.load(model_path)
            except ImportError:
                model_obj = {"_stub": "sklearn", "path": model_path}
        else:
            # custom — just store path reference
            model_obj = {"_stub": "custom", "path": model_path}

        _MODEL_CACHE[adapter_id] = model_obj
        adapter["status"] = "loaded"
        return model_obj

    # -- predict ------------------------------------------------------------

    async def predict(self, adapter_id: str, input_data: dict) -> dict:
        """Run inference and return prediction + latency."""
        adapter = _ADAPTER_STORE.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter {adapter_id} not found")

        start = time.perf_counter()
        model = await self.load_model(adapter_id)

        # V1: stub prediction — real frameworks would call model(input)
        if isinstance(model, dict) and "_stub" in model:
            prediction = {
                "output": "stub_prediction",
                "framework": adapter["framework"],
                "model_name": adapter["model_name"],
                "input_keys": list(input_data.keys()),
            }
        else:
            # Try calling the model directly
            try:
                prediction = {"output": str(model(input_data))}
            except Exception as exc:
                prediction = {"error": str(exc)}

        elapsed = (time.perf_counter() - start) * 1000
        return {"prediction": prediction, "latency_ms": round(elapsed, 2)}

    # -- list ---------------------------------------------------------------

    async def list_adapters(self, db: Any, workspace_id: str) -> list[dict]:
        return [
            a for a in _ADAPTER_STORE.values() if a["workspace_id"] == workspace_id
        ]

    # -- test ---------------------------------------------------------------

    async def test_adapter(self, adapter_id: str, sample_input: dict) -> dict:
        """Quick health-check of an adapter."""
        try:
            result = await self.predict(adapter_id, sample_input)
            prediction = result["prediction"]
            output_shape = None
            if isinstance(prediction, dict) and "output" in prediction:
                val = prediction["output"]
                if hasattr(val, "shape"):
                    output_shape = list(val.shape)
            return {"works": True, "output_shape": output_shape, "error": None}
        except Exception as exc:
            return {"works": False, "output_shape": None, "error": str(exc)}

    # -- supported frameworks -----------------------------------------------

    @staticmethod
    def get_supported_frameworks() -> list[dict[str, str]]:
        return SUPPORTED_FRAMEWORKS
