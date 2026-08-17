"""BYOM (Bring Your Own Model) routes — validate, register, list custom models."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.plugin import BYOMModel

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


# Registered models live in the byom_models table. A registration that
# disappears on restart leaves the pipeline node it created pointing at
# nothing.


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


def _model_out(model: BYOMModel) -> BYOMModelResponse:
    return BYOMModelResponse(
        model_id=str(model.id),
        model_name=model.model_name,
        model_type=model.model_type,
        file_name=model.file_name,
        status=model.status,
        node_name=model.node_name,
        created_at=model.created_at.isoformat() if model.created_at else "",
        input_shape=model.input_shape,
        output_shape=model.output_shape,
    )


@router.post("/register", response_model=BYOMModelResponse, status_code=201)
async def register_model(
    body: BYOMRegisterRequest,
    workspace_id: UUID | None = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> BYOMModelResponse:
    """Register a validated BYOM model and create its pipeline node entry."""
    model = BYOMModel(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        model_name=body.model_name,
        model_type=body.model_type,
        file_name=body.file_name,
        input_shape=body.input_shape,
        output_shape=body.output_shape,
        adapter=body.adapter.model_dump(),
        node_name=body.node.node_name,
        node_config=body.node.model_dump(),
        status="registered",
    )
    db.add(model)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A model named '{body.model_name}' is already registered",
        )
    await db.refresh(model)

    return _model_out(model)


@router.get("/models", response_model=list[BYOMModelResponse])
async def list_models(
    workspace_id: UUID | None = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> list[BYOMModelResponse]:
    """List registered BYOM models, scoped to a workspace when given."""
    query = select(BYOMModel)
    if workspace_id is not None:
        query = query.where(BYOMModel.workspace_id == workspace_id)

    result = await db.execute(query.order_by(BYOMModel.created_at))
    return [_model_out(m) for m in result.scalars().all()]


@router.delete("/models/{model_id}", status_code=204, response_class=Response)
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a registered BYOM model."""
    result = await db.execute(select(BYOMModel).where(BYOMModel.id == model_id))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    await db.delete(model)
    await db.commit()
    return Response(status_code=204)
