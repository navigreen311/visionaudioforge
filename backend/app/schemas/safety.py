"""Pydantic schemas for Safety & Privacy endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PIIMatch(BaseModel):
    """A single PII detection match."""

    type: str = Field(..., description="PII type: email, phone, ssn, credit_card")
    value: str = Field(..., description="The matched PII string")
    position: list[int] = Field(..., description="[start, end] character positions")


class SafetyScanResult(BaseModel):
    """Result from scanning an image or text for safety concerns."""

    faces_detected: int = Field(0, description="Number of faces detected")
    face_locations: list[list[int]] = Field(default_factory=list, description="Bounding boxes [x, y, w, h]")
    pii_found: list[PIIMatch] = Field(default_factory=list, description="PII matches found")
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall risk score 0-1")
    recommendations: list[str] = Field(default_factory=list, description="Safety recommendations")


class RedactionResult(BaseModel):
    """Result from PII redaction."""

    redacted_text: str = Field(..., description="Text with PII replaced by placeholders")
    redactions: list[dict] = Field(default_factory=list, description="List of redactions applied")


class SafetyReport(BaseModel):
    """Aggregated safety report across multiple scans."""

    total_scans: int = Field(0, description="Total number of scans aggregated")
    faces_found: int = Field(0, description="Total faces found across scans")
    pii_instances: int = Field(0, description="Total PII instances found")
    avg_risk_score: float = Field(0.0, description="Average risk score")
    recommendations: list[str] = Field(default_factory=list, description="Aggregated recommendations")


class ContentSafetyResult(BaseModel):
    """Result from content safety check."""

    safe: bool = Field(True, description="Whether the content is considered safe")
    flags: list[str] = Field(default_factory=list, description="Safety flags raised")


class RedactRequest(BaseModel):
    """Request body for PII redaction."""

    text: str = Field(..., description="Text to scan and redact")


class ReportRequest(BaseModel):
    """Request body for safety report generation."""

    scan_ids: list[str] = Field(default_factory=list, description="Scan result IDs to aggregate")
