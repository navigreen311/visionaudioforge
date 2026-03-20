"""Pydantic response models for VisionAudioForge SDK."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------- Vision types ----------

class Detection(BaseModel):
    label: str
    confidence: float
    bbox: list[float] = Field(default_factory=list, description="[x1, y1, x2, y2]")


class FlowResult(BaseModel):
    method: str
    flow_vectors: Any | None = None
    magnitude_mean: float | None = None
    magnitude_max: float | None = None


class OCRResult(BaseModel):
    text: str
    confidence: float | None = None
    regions: list[dict[str, Any]] = Field(default_factory=list)


class SegmentationResult(BaseModel):
    masks: list[dict[str, Any]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)


class TrackingResult(BaseModel):
    tracks: list[dict[str, Any]] = Field(default_factory=list)
    frame_count: int = 0


class AnalysisResult(BaseModel):
    detections: list[Detection] = Field(default_factory=list)
    ocr: OCRResult | None = None
    segmentation: SegmentationResult | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------- Audio types ----------

class AudioAnalysis(BaseModel):
    duration: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class Transcript(BaseModel):
    text: str
    segments: list[dict[str, Any]] = Field(default_factory=list)
    language: str | None = None


class DiarizationResult(BaseModel):
    speakers: list[dict[str, Any]] = Field(default_factory=list)
    num_speakers: int = 0


class Classification(BaseModel):
    label: str
    confidence: float
    scores: dict[str, float] = Field(default_factory=dict)


# ---------- Model types ----------

class Model(BaseModel):
    id: str
    name: str
    version: str
    backbone: str | None = None
    status: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class Comparison(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_a: Model | None = None
    model_b: Model | None = None
    metrics_diff: dict[str, Any] = Field(default_factory=dict)


class TrainingJob(BaseModel):
    id: str
    status: str
    config: dict[str, Any] = Field(default_factory=dict)


class Experiment(BaseModel):
    id: str
    name: str | None = None
    runs: list[dict[str, Any]] = Field(default_factory=list)


# ---------- Search types ----------

class SearchResult(BaseModel):
    asset_id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexResult(BaseModel):
    asset_id: str
    status: str
    indexed_at: str | None = None


# ---------- Pipeline types ----------

class Pipeline(BaseModel):
    id: str
    name: str
    definition: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None


class PipelineRun(BaseModel):
    id: str
    pipeline_id: str
    status: str
    results: dict[str, Any] = Field(default_factory=dict)


# ---------- Agent types ----------

class Agent(BaseModel):
    id: str
    name: str
    skill_pack: str | None = None
    status: str | None = None


class Memory(BaseModel):
    id: str
    content: str
    timestamp: str | None = None


# ---------- Dataset types ----------

class Dataset(BaseModel):
    id: str
    name: str
    size: int | None = None
    format: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetVersion(BaseModel):
    id: str
    dataset_id: str
    version: str
    created_at: str | None = None


# ---------- Alert types ----------

class Alert(BaseModel):
    id: str
    type: str
    message: str
    severity: str | None = None
    created_at: str | None = None


# ---------- Asset types ----------

class Asset(BaseModel):
    id: str
    name: str
    type: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------- Transform types ----------

class TransformResult(BaseModel):
    id: str | None = None
    status: str
    output_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
