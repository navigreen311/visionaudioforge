"""Pydantic schemas for the ReviewOps system."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Review Task
# ------------------------------------------------------------------


class ReviewTaskCreate(BaseModel):
    asset_id: UUID
    review_type: Literal[
        "annotation_qa", "detection_verify", "alert_review",
        "content_moderation", "model_output_check",
    ]
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    required_reviews: int = Field(1, ge=1, le=5)
    sla_hours: float = Field(24.0, gt=0)


class ReviewTaskRead(BaseModel):
    task_id: UUID
    workspace_id: UUID
    asset_id: UUID
    review_type: str
    priority: str
    status: str
    required_reviews: int
    sla_hours: float
    sla_deadline: datetime
    assigned_to: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    reviews: list["ReviewRead"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Review
# ------------------------------------------------------------------


class ReviewSubmit(BaseModel):
    decision: Literal["approved", "rejected", "needs_correction", "escalated"]
    score: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None
    corrections: Optional[dict[str, Any]] = None


class ReviewRead(BaseModel):
    review_id: UUID
    task_id: UUID
    reviewer_id: UUID
    decision: str
    score: Optional[int] = None
    notes: Optional[str] = None
    corrections: Optional[dict[str, Any]] = None
    review_time_seconds: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Assignment
# ------------------------------------------------------------------


class AssignReviewer(BaseModel):
    reviewer_id: UUID
    auto: bool = False


class AssignmentResult(BaseModel):
    assigned_to: UUID
    assigned_at: datetime


class AutoAssignResult(BaseModel):
    assigned: int


# ------------------------------------------------------------------
# SLA
# ------------------------------------------------------------------


class SLABreach(BaseModel):
    task_id: UUID
    sla_deadline: datetime
    overdue_hours: float
    status: str
    review_type: str


# ------------------------------------------------------------------
# Workload
# ------------------------------------------------------------------


class ReviewerWorkload(BaseModel):
    reviewer_id: UUID
    active_tasks: int
    completed_today: int
    avg_review_time_s: float


# ------------------------------------------------------------------
# Double Review
# ------------------------------------------------------------------


class ReviewCompletion(BaseModel):
    complete: bool
    reviews_received: int
    reviews_required: int
    consensus: bool
    disagreement: Optional[list[dict[str, Any]]] = None


class DisagreementResolve(BaseModel):
    senior_reviewer_id: UUID
    final_decision: Literal["approved", "rejected", "needs_correction"]


class InterReviewerAgreement(BaseModel):
    agreement_rate: float
    total_double_reviewed: int
    disagreements: int
    by_review_type: dict[str, Any]


# ------------------------------------------------------------------
# Quality Scoring
# ------------------------------------------------------------------


class ReviewerScore(BaseModel):
    reviewer_id: UUID
    total_reviews: int
    avg_quality_score: float
    avg_review_time_s: float
    sla_compliance_pct: float
    agreement_rate: float
    overall_grade: str


class AssetQualityScore(BaseModel):
    score: float
    reviews: list[dict[str, Any]]
    consensus: bool


class QualityTrend(BaseModel):
    period: str
    avg_score: float
    review_count: int
    sla_compliance: float


# ------------------------------------------------------------------
# Shift Management
# ------------------------------------------------------------------


class ShiftCreate(BaseModel):
    reviewer_id: UUID
    start: datetime
    end: datetime
    review_types: Optional[list[str]] = None


class ShiftRead(BaseModel):
    shift_id: UUID
    workspace_id: UUID
    reviewer_id: UUID
    start_time: datetime
    end_time: datetime
    review_types: Optional[list[str]] = None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HandoffRequest(BaseModel):
    to_shift_id: UUID
    notes: str


class HandoffResult(BaseModel):
    pending_tasks_transferred: int


class ShiftReport(BaseModel):
    reviewer: UUID
    duration_h: float
    tasks_completed: int
    avg_quality: float
    sla_breaches: int
