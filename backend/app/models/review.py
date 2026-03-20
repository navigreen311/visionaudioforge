"""SQLAlchemy models for the ReviewOps system."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReviewTaskStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    in_review = "in_review"
    completed = "completed"
    escalated = "escalated"


class ReviewType(str, enum.Enum):
    annotation_qa = "annotation_qa"
    detection_verify = "detection_verify"
    alert_review = "alert_review"
    content_moderation = "content_moderation"
    model_output_check = "model_output_check"


class ReviewPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class ReviewDecision(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    needs_correction = "needs_correction"
    escalated = "escalated"


class ReviewTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_tasks"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    review_type = Column(Enum(ReviewType), nullable=False)
    priority = Column(Enum(ReviewPriority), nullable=False, default=ReviewPriority.normal)
    status = Column(Enum(ReviewTaskStatus), nullable=False, default=ReviewTaskStatus.pending)
    required_reviews = Column(Integer, nullable=False, default=1)
    sla_hours = Column(Float, nullable=False, default=24.0)
    sla_deadline = Column(DateTime(timezone=True), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reviews = relationship("Review", back_populates="task", cascade="all, delete-orphan")


class Review(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    task_id = Column(UUID(as_uuid=True), ForeignKey("review_tasks.id"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decision = Column(Enum(ReviewDecision), nullable=False)
    score = Column(Integer, nullable=True)  # 1-5
    notes = Column(Text, nullable=True)
    corrections = Column(JSON, nullable=True)
    review_time_seconds = Column(Float, nullable=True)

    # Relationships
    task = relationship("ReviewTask", back_populates="reviews")


class ReviewShift(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_shifts"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    review_types = Column(JSON, nullable=True)  # list of ReviewType values
    notes = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
