"""SafetyScanner — face detection, PII detection, redaction, and reporting."""

from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np


# PII regex patterns
_PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
}

_REDACTION_LABELS: dict[str, str] = {
    "email": "[REDACTED_EMAIL]",
    "phone": "[REDACTED_PHONE]",
    "ssn": "[REDACTED_SSN]",
    "credit_card": "[REDACTED_CREDIT_CARD]",
}


class SafetyScanner:
    """Scans images and text for privacy / safety concerns."""

    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)

    # ------------------------------------------------------------------
    # Face helpers
    # ------------------------------------------------------------------

    def detect_faces(self, image: np.ndarray) -> list[list[int]]:
        """Return list of face bounding boxes ``[x, y, w, h]``."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        if len(faces) == 0:
            return []
        return [list(map(int, f)) for f in faces]

    # ------------------------------------------------------------------
    # PII helpers
    # ------------------------------------------------------------------

    @staticmethod
    def detect_text_pii(text: str) -> list[dict[str, Any]]:
        """Return list of PII matches with type, value, and position."""
        matches: list[dict[str, Any]] = []
        for pii_type, pattern in _PII_PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append(
                    {
                        "type": pii_type,
                        "value": m.group(),
                        "position": [m.start(), m.end()],
                    }
                )
        return matches

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def scan_image(self, image: np.ndarray) -> dict[str, Any]:
        """Scan an image for faces and return a safety result dict."""
        face_locations = self.detect_faces(image)
        faces_detected = len(face_locations)

        # Risk score: more faces → higher risk (capped at 1.0)
        risk_score = min(faces_detected * 0.2, 1.0)

        recommendations: list[str] = []
        if faces_detected > 0:
            recommendations.append("Consider blurring detected faces before publishing.")
        if faces_detected > 3:
            recommendations.append("Multiple faces detected — review group-photo privacy policy.")

        return {
            "faces_detected": faces_detected,
            "face_locations": face_locations,
            "pii_found": [],
            "risk_score": risk_score,
            "recommendations": recommendations,
        }

    async def blur_faces(
        self, image: np.ndarray, face_locations: list[list[int]] | None = None
    ) -> np.ndarray:
        """Apply Gaussian blur to each detected face region."""
        if face_locations is None:
            face_locations = self.detect_faces(image)

        result = image.copy()
        for x, y, w, h in face_locations:
            roi = result[y : y + h, x : x + w]
            blurred_roi = cv2.GaussianBlur(roi, (99, 99), 30)
            result[y : y + h, x : x + w] = blurred_roi
        return result

    async def redact_pii(self, text: str) -> dict[str, Any]:
        """Replace PII in *text* with redaction placeholders."""
        matches = self.detect_text_pii(text)

        # Sort by position descending so replacements don't shift indices
        sorted_matches = sorted(matches, key=lambda m: m["position"][0], reverse=True)

        redacted = text
        redactions: list[dict[str, Any]] = []
        for m in sorted_matches:
            start, end = m["position"]
            label = _REDACTION_LABELS.get(m["type"], "[REDACTED]")
            redacted = redacted[:start] + label + redacted[end:]
            redactions.append(
                {
                    "type": m["type"],
                    "original": m["value"],
                    "position": [start, end],
                }
            )

        # Return redactions in original (ascending) order
        redactions.reverse()
        return {"redacted_text": redacted, "redactions": redactions}

    async def scan_audio_pii(self, transcript: str) -> list[dict[str, Any]]:
        """Scan an audio transcript for PII (delegates to text PII detection)."""
        return self.detect_text_pii(transcript)

    async def generate_safety_report(self, scan_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate multiple scan results into a single safety report."""
        total_scans = len(scan_results)
        faces_found = sum(r.get("faces_detected", 0) for r in scan_results)
        pii_instances = sum(len(r.get("pii_found", [])) for r in scan_results)
        risk_scores = [r.get("risk_score", 0.0) for r in scan_results]
        avg_risk = sum(risk_scores) / total_scans if total_scans else 0.0

        # Deduplicate recommendations
        all_recs: list[str] = []
        seen: set[str] = set()
        for r in scan_results:
            for rec in r.get("recommendations", []):
                if rec not in seen:
                    seen.add(rec)
                    all_recs.append(rec)

        return {
            "total_scans": total_scans,
            "faces_found": faces_found,
            "pii_instances": pii_instances,
            "avg_risk_score": round(avg_risk, 4),
            "recommendations": all_recs,
        }
