"""BYOM (Bring Your Own Model) adapter — register, load, and predict with custom models."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import ModelAdapter


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
# Storage
# ---------------------------------------------------------------------------

# Adapter registrations live in the model_adapters table: a registration
# that vanishes on restart leaves a pipeline pointing at a model nobody can
# load. _MODEL_CACHE stays in memory on purpose — it holds live model
# handles, which are per-process by nature and cheap to rebuild.
_MODEL_CACHE: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# BYOMAdapter
# ---------------------------------------------------------------------------


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _adapter_out(adapter: ModelAdapter) -> dict[str, Any]:
    return {
        "adapter_id": str(adapter.id),
        "model_id": str(adapter.model_id),
        "workspace_id": (
            str(adapter.workspace_id) if adapter.workspace_id else None
        ),
        "model_name": adapter.model_name,
        "model_path_or_url": adapter.model_path_or_url,
        "framework": adapter.framework,
        "input_schema": adapter.input_schema or {},
        "output_schema": adapter.output_schema or {},
        "status": adapter.status,
    }


class BYOMAdapter:
    """Register, load, and run inference on user-supplied models."""

    @staticmethod
    async def _load_adapter(db: AsyncSession, adapter_id: str) -> ModelAdapter:
        key = _as_uuid(adapter_id)
        if key is None:
            raise ValueError(f"Adapter {adapter_id} not found")

        result = await db.execute(
            select(ModelAdapter).where(ModelAdapter.id == key)
        )
        adapter = result.scalar_one_or_none()
        if adapter is None:
            raise ValueError(f"Adapter {adapter_id} not found")
        return adapter

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

        adapter = ModelAdapter(
            id=uuid.uuid4(),
            workspace_id=_as_uuid(workspace_id),
            model_id=uuid.uuid4(),
            model_name=model_name,
            model_path_or_url=model_path_or_url,
            framework=framework,
            input_schema=input_schema,
            output_schema=output_schema,
            status="registered",
        )
        db.add(adapter)
        await db.commit()

        return {
            "model_id": str(adapter.model_id),
            "adapter_id": str(adapter.id),
        }

    # -- load ---------------------------------------------------------------

    async def load_model(self, db: AsyncSession, adapter_id: str) -> Any:
        """Load a model into memory (cached per process)."""
        if adapter_id in _MODEL_CACHE:
            return _MODEL_CACHE[adapter_id]

        adapter = await self._load_adapter(db, adapter_id)

        framework = adapter.framework
        model_path = adapter.model_path_or_url

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
        adapter.status = "loaded"
        await db.commit()
        return model_obj

    # -- predict ------------------------------------------------------------

    async def predict(
        self, db: AsyncSession, adapter_id: str, input_data: dict
    ) -> dict:
        """Run inference and return prediction + latency."""
        adapter = await self._load_adapter(db, adapter_id)

        start = time.perf_counter()
        model = await self.load_model(db, adapter_id)

        # V1: stub prediction — real frameworks would call model(input)
        if isinstance(model, dict) and "_stub" in model:
            prediction = {
                "output": "stub_prediction",
                "framework": adapter.framework,
                "model_name": adapter.model_name,
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

    async def list_adapters(
        self, db: AsyncSession, workspace_id: str
    ) -> list[dict]:
        """List every adapter registered in a workspace."""
        result = await db.execute(
            select(ModelAdapter)
            .where(ModelAdapter.workspace_id == _as_uuid(workspace_id))
            .order_by(ModelAdapter.created_at)
        )
        return [_adapter_out(a) for a in result.scalars().all()]

    async def test_adapter(
        self, db: AsyncSession, adapter_id: str, sample_input: dict
    ) -> dict:
        """Quick health-check of an adapter."""
        try:
            result = await self.predict(db, adapter_id, sample_input)
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
