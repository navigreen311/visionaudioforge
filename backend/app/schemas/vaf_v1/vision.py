"""Schemas for /api/v1/vision/*.

Mirrors DocumentAnalysis and ScreenAnalysis shapes from the PAF VAF spec.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

DocumentType = Literal["invoice", "contract", "compliance", "medical", "general"]


# ---------------------------------------------------------------------------
# Document analysis
# ---------------------------------------------------------------------------


class DocumentTable(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class DocumentSignature(BaseModel):
    present: bool
    signedBy: Optional[str] = None
    date: Optional[str] = None


class DocumentExpiration(BaseModel):
    field: str
    date: str
    isExpired: bool


class DocumentCompliance(BaseModel):
    issues: list[str] = Field(default_factory=list)
    missingFields: list[str] = Field(default_factory=list)
    expirations: list[DocumentExpiration] = Field(default_factory=list)


class DocumentAnalysis(BaseModel):
    type: DocumentType
    extractedFields: dict[str, str] = Field(default_factory=dict)
    tables: list[DocumentTable] = Field(default_factory=list)
    signatures: list[DocumentSignature] = Field(default_factory=list)
    summary: str
    compliance: DocumentCompliance


# ---------------------------------------------------------------------------
# Screen analysis
# ---------------------------------------------------------------------------


class ScreenElementPosition(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ScreenElement(BaseModel):
    type: str
    label: str
    position: ScreenElementPosition
    state: Optional[str] = None
    value: Optional[str] = None


class ScreenAnalysis(BaseModel):
    elements: list[ScreenElement]
    currentPage: str
    activeModal: Optional[str] = None
    errors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
