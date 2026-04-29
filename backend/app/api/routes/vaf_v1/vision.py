"""VAF v1 — Vision endpoints (document and screen)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.schemas.vaf_v1.vision import (
    DocumentAnalysis,
    DocumentCompliance,
    DocumentExpiration,
    DocumentSignature,
    DocumentTable,
    DocumentType,
    ScreenAnalysis,
    ScreenElement,
    ScreenElementPosition,
)

from ._auth_shim import vaf_auth

router = APIRouter(prefix="/api/v1/vision", tags=["vaf-v1-vision"])


def _classify_document(filename: str, mime_type: str) -> DocumentType:
    """Heuristic mock classifier — picks a type based on the filename.

    Lets tests verify the variant logic without standing up a real model.
    """
    name = (filename or "").lower()
    if "invoice" in name:
        return "invoice"
    if "compliance" in name:
        return "compliance"
    if "contract" in name:
        return "contract"
    if "medical" in name or "patient" in name:
        return "medical"
    return "general"


def _build_invoice_analysis(filename: str) -> DocumentAnalysis:
    return DocumentAnalysis(
        type="invoice",
        extractedFields={
            "invoiceNumber": "INV-2026-0481",
            "vendor": "Oak Valley Supplies",
            "totalAmount": "$4,820.00",
            "dueDate": "2026-05-15",
        },
        tables=[
            DocumentTable(
                headers=["Item", "Qty", "Unit Price", "Total"],
                rows=[
                    ["Widget A", "10", "$120.00", "$1,200.00"],
                    ["Widget B", "5", "$724.00", "$3,620.00"],
                ],
            )
        ],
        signatures=[DocumentSignature(present=False)],
        summary=f"Invoice from Oak Valley Supplies totalling $4,820.00, due 2026-05-15. (file: {filename})",
        compliance=DocumentCompliance(),
    )


def _build_compliance_analysis(filename: str) -> DocumentAnalysis:
    return DocumentAnalysis(
        type="compliance",
        extractedFields={
            "facility": "MedLink Pro",
            "reportPeriod": "Q1 2026",
        },
        tables=[],
        signatures=[
            DocumentSignature(present=True, signedBy="Compliance Officer", date="2026-04-01"),
        ],
        summary=f"HCQC compliance report for MedLink Pro, Q1 2026. (file: {filename})",
        compliance=DocumentCompliance(
            issues=[
                "TB clearance for Maria Santos expired Feb 15",
                "CPR certification for James Lee expires in 3 days",
            ],
            missingFields=["BackgroundCheckStatus"],
            expirations=[
                DocumentExpiration(field="TB Clearance — Maria Santos", date="2026-02-15", isExpired=True),
                DocumentExpiration(field="CPR Cert — James Lee", date="2026-05-01", isExpired=False),
            ],
        ),
    )


def _build_general_analysis(filename: str, mime_type: str) -> DocumentAnalysis:
    return DocumentAnalysis(
        type="general",
        extractedFields={"filename": filename or "(unnamed)", "mimeType": mime_type or "application/octet-stream"},
        tables=[],
        signatures=[DocumentSignature(present=False)],
        summary=f"General document — no specialised classifier matched. (file: {filename})",
        compliance=DocumentCompliance(),
    )


@router.post("/document", response_model=DocumentAnalysis)
async def analyze_document(
    file: UploadFile = File(...),
    mimeType: str = Form(""),
    _token: str = Depends(vaf_auth),
) -> DocumentAnalysis:
    """Analyse an uploaded document (PDF, image, scan).

    The mock dispatches on filename so tests can verify each variant of
    the response shape without uploading real PDFs.
    """
    # Drain the upload stream — real impl would hand bytes to OCR/LLM.
    await file.read()

    effective_mime = mimeType or (file.content_type or "")
    doc_type = _classify_document(file.filename or "", effective_mime)

    if doc_type == "invoice":
        return _build_invoice_analysis(file.filename or "")
    if doc_type == "compliance":
        return _build_compliance_analysis(file.filename or "")
    if doc_type == "contract":
        return DocumentAnalysis(
            type="contract",
            extractedFields={"parties": "Party A; Party B", "effectiveDate": "2026-04-01"},
            tables=[],
            signatures=[
                DocumentSignature(present=True, signedBy="Party A", date="2026-04-01"),
                DocumentSignature(present=True, signedBy="Party B", date="2026-04-01"),
            ],
            summary=f"Bilateral contract between Party A and Party B effective 2026-04-01. (file: {file.filename or ''})",
            compliance=DocumentCompliance(),
        )
    if doc_type == "medical":
        return DocumentAnalysis(
            type="medical",
            extractedFields={"patient": "REDACTED", "provider": "Dr. Martinez"},
            tables=[],
            signatures=[DocumentSignature(present=True, signedBy="Dr. Martinez", date="2026-04-20")],
            summary=f"Medical record (PHI redacted). (file: {file.filename or ''})",
            compliance=DocumentCompliance(),
        )
    return _build_general_analysis(file.filename or "", effective_mime)


@router.post("/screen", response_model=ScreenAnalysis)
async def analyze_screen(
    image: UploadFile = File(...),
    _token: str = Depends(vaf_auth),
) -> ScreenAnalysis:
    """Analyse an uploaded screenshot for UI guidance.

    Mock returns five plausible UI elements with positions Shadow can use
    to drive its 'point-and-click' coaching fallback.
    """
    await image.read()

    elements = [
        ScreenElement(
            type="button",
            label="Save",
            position=ScreenElementPosition(x=820.0, y=640.0, width=96.0, height=36.0),
            state="enabled",
        ),
        ScreenElement(
            type="button",
            label="Cancel",
            position=ScreenElementPosition(x=712.0, y=640.0, width=96.0, height=36.0),
            state="enabled",
        ),
        ScreenElement(
            type="input",
            label="Email",
            position=ScreenElementPosition(x=240.0, y=320.0, width=420.0, height=40.0),
            state="enabled",
            value="",
        ),
        ScreenElement(
            type="input",
            label="Password",
            position=ScreenElementPosition(x=240.0, y=380.0, width=420.0, height=40.0),
            state="enabled",
            value="",
        ),
        ScreenElement(
            type="card",
            label="Account Settings",
            position=ScreenElementPosition(x=120.0, y=120.0, width=720.0, height=480.0),
            state="active",
        ),
    ]

    return ScreenAnalysis(
        elements=elements,
        currentPage="account/settings",
        activeModal=None,
        errors=[],
        suggestions=["Fill in the Email field, then click Save to continue."],
    )
