"""Auto-label stub — returns mock detection suggestions for annotation."""

from __future__ import annotations

import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/annotate", tags=["auto-label"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------


class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class AutoLabelRequest(BaseModel):
    image_b64: str = Field(..., description="Base-64 encoded image data")
    labels: list[str] = Field(..., description="Available label names to detect")


class AutoLabelSuggestion(BaseModel):
    id: str
    label: str
    confidence: float
    bbox: BBox


class AutoLabelResponse(BaseModel):
    suggestions: list[AutoLabelSuggestion]


# ------------------------------------------------------------------
# Route
# ------------------------------------------------------------------


@router.post("/auto-label", response_model=AutoLabelResponse)
async def auto_label(body: AutoLabelRequest) -> AutoLabelResponse:
    """Return mock auto-label suggestions.

    In production this would run an object-detection model (e.g. YOLO,
    Faster R-CNN, or a CLIP-based zero-shot detector) against the
    supplied image using the requested label vocabulary.
    """

    # Pick up to 3 labels from the request (cycle if fewer provided)
    label_pool = body.labels if body.labels else ["object"]

    mock_suggestions: list[AutoLabelSuggestion] = [
        AutoLabelSuggestion(
            id=str(uuid.uuid4()),
            label=label_pool[0 % len(label_pool)],
            confidence=0.92,
            bbox=BBox(x=50, y=30, width=200, height=150),
        ),
        AutoLabelSuggestion(
            id=str(uuid.uuid4()),
            label=label_pool[1 % len(label_pool)],
            confidence=0.78,
            bbox=BBox(x=300, y=100, width=120, height=180),
        ),
        AutoLabelSuggestion(
            id=str(uuid.uuid4()),
            label=label_pool[2 % len(label_pool)],
            confidence=0.45,
            bbox=BBox(x=500, y=200, width=160, height=90),
        ),
    ]

    return AutoLabelResponse(suggestions=mock_suggestions)
