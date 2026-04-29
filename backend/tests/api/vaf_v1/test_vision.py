"""Tests for /api/v1/vision/* (WS11)."""

from __future__ import annotations

import io

import pytest

from .intel_router import build_intel_client


@pytest.fixture
def client():
    return build_intel_client()


# ---------------------------------------------------------------------------
# /vision/document
# ---------------------------------------------------------------------------


def _doc_upload(filename: str, mime_type: str = "application/pdf") -> dict:
    buf = io.BytesIO(b"%PDF-1.4 test bytes")
    return {"file": (filename, buf, mime_type)}


def test_vision_document_invoice_variant(client):
    res = client.post(
        "/api/v1/vision/document",
        files=_doc_upload("Q1-invoice.pdf"),
        data={"mimeType": "application/pdf"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["type"] == "invoice"
    assert "invoiceNumber" in data["extractedFields"]
    assert len(data["tables"]) >= 1
    assert data["compliance"]["issues"] == []


def test_vision_document_compliance_variant_has_issues(client):
    res = client.post(
        "/api/v1/vision/document",
        files=_doc_upload("hcqc-compliance-report.pdf"),
        data={"mimeType": "application/pdf"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["type"] == "compliance"
    assert 1 <= len(data["compliance"]["issues"]) <= 5
    assert any(exp["isExpired"] for exp in data["compliance"]["expirations"])


def test_vision_document_general_fallback(client):
    res = client.post(
        "/api/v1/vision/document",
        files=_doc_upload("random_notes.txt", "text/plain"),
        data={"mimeType": "text/plain"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["type"] == "general"


def test_vision_document_missing_file_returns_422(client):
    res = client.post("/api/v1/vision/document", data={"mimeType": "application/pdf"})
    assert res.status_code == 422


def test_vision_document_response_shape(client):
    res = client.post(
        "/api/v1/vision/document",
        files=_doc_upload("contract-v2.pdf"),
        data={"mimeType": "application/pdf"},
    )
    assert res.status_code == 200
    data = res.json()
    for key in ("type", "extractedFields", "tables", "signatures", "summary", "compliance"):
        assert key in data
    for key in ("issues", "missingFields", "expirations"):
        assert key in data["compliance"]


# ---------------------------------------------------------------------------
# /vision/screen
# ---------------------------------------------------------------------------


def test_vision_screen_happy_path(client):
    img = io.BytesIO(b"\x89PNG\r\n\x1a\nfake")
    res = client.post(
        "/api/v1/vision/screen",
        files={"image": ("screen.png", img, "image/png")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["elements"]) == 5

    labels = {e["label"] for e in data["elements"]}
    assert "Save" in labels
    assert "Email" in labels

    for el in data["elements"]:
        for key in ("type", "label", "position"):
            assert key in el
        for k in ("x", "y", "width", "height"):
            assert k in el["position"]

    assert data["currentPage"]
    assert isinstance(data["errors"], list)
    assert isinstance(data["suggestions"], list)


def test_vision_screen_missing_image_returns_422(client):
    res = client.post("/api/v1/vision/screen")
    assert res.status_code == 422
