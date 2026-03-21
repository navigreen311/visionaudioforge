"""BYOM (Bring Your Own Model) routes — validate, register, list custom models."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/marketplace/byom", tags=["byom"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdapterConfigSchema(BaseModel):
    resize_w: int = 224
    resize_h: int = 224
    normalize: bool = True
    mean: list[float] = Field(default_factory=lambda: [0.485, 0.456, 0.406])
    std: list[float] = Field(default_factory=lambda: [0.229, 0.224, 0.225])
    color_space: str = "RGB"
    output_type: str = "probabilities"
    classes: str = ""
    confidence_threshold: float = 0.5


class NodeConfigSchema(BaseModel):
    node_name: str
    category: str = "Vision"
    icon: str = "Brain"


class BYOMRegisterRequest(BaseModel):
    model_name: str
    model_type: str
    file_name: str = ""
    input_shape: str = ""
    output_shape: str = ""
    adapter: AdapterConfigSchema = Field(default_factory=AdapterConfigSchema)
    node: NodeConfigSchema


class BYOMModelResponse(BaseModel):
    model_id: str
    model_name: str
    model_type: str
    file_name: str
    status: str
    node_name: str | None
    created_at: str
    input_shape: str
    output_shape: str


class ValidationResponse(BaseModel):
    valid: bool
    input_shape: str
    output_shape: str
    framework_detected: str
    param_count: int


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_models: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".onnx", ".pt", ".pth", ".tflite"}


@router.post("/validate", response_model=ValidationResponse)
async def validate_model(
    file: UploadFile = File(...),
    model_name: str = Form(""),
    model_type: str = Form("Classification"),
) -> ValidationResponse:
    """Validate an uploaded model file.

    Stub: inspects the file extension and returns a mock validation result.
    Real implementation would load the model, inspect graph I/O, and count params.
    """
    filename = file.filename or ""
    ext = ""
    dot_idx = filename.rfind(".")
    if dot_idx >= 0:
        ext = filename[dot_idx:].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Stub: simulate validation based on model_type
    shape_map: dict[str, tuple[str, str]] = {
        "Classification": ("1x3x224x224", "1x1000"),
        "Detection": ("1x3x640x640", "1x100x6"),
        "Segmentation": ("1x3x512x512", "1x21x512x512"),
        "Audio": ("1x1x16000", "1x512"),
        "Embedding": ("1x3x224x224", "1x768"),
        "Custom": ("1x3x224x224", "1xN"),
    }

    input_shape, output_shape = shape_map.get(model_type, ("1x3x224x224", "1xN"))

    framework_map: dict[str, str] = {
        ".onnx": "ONNX Runtime",
        ".pt": "PyTorch",
        ".pth": "PyTorch",
        ".tflite": "TensorFlow Lite",
    }

    return ValidationResponse(
        valid=True,
        input_shape=input_shape,
        output_shape=output_shape,
        framework_detected=framework_map.get(ext, "Unknown"),
        param_count=25_600_000,  # stub
    )


@router.post("/register", response_model=BYOMModelResponse)
async def register_model(body: BYOMRegisterRequest) -> BYOMModelResponse:
    """Register a validated BYOM model and create its pipeline node entry."""
    model_id = str(uuid.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    record: dict[str, Any] = {
        "model_id": model_id,
        "model_name": body.model_name,
        "model_type": body.model_type,
        "file_name": body.file_name,
        "status": "registered",
        "node_name": body.node.node_name,
        "created_at": now,
        "input_shape": body.input_shape,
        "output_shape": body.output_shape,
        "adapter": body.adapter.model_dump(),
        "node": body.node.model_dump(),
    }
    _models[model_id] = record

    return BYOMModelResponse(**{k: record[k] for k in BYOMModelResponse.model_fields})


@router.get("/models", response_model=list[BYOMModelResponse])
async def list_models() -> list[BYOMModelResponse]:
    """List all registered BYOM models."""
    return [
        BYOMModelResponse(**{k: m[k] for k in BYOMModelResponse.model_fields})
        for m in _models.values()
    ]
