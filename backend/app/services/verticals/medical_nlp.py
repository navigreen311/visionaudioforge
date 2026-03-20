"""Medical NLP service for clinical text processing.

Provides medical term extraction, clinical note structuring,
and PHI de-identification for HIPAA-compliant text handling.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Regex pattern sets for medical term extraction
# ---------------------------------------------------------------------------

# Common drug name patterns (generic / brand-name stems)
_DRUG_PATTERNS = re.compile(
    r"\b("
    r"[A-Za-z]+-?(?:mab|nib|vir|olol|pril|sartan|statin|azole|cillin|mycin|cycline"
    r"|prazole|lukast|gliptin|flozin|tide|pine|lol|pam|lam|done|ine|ate)"
    r"|aspirin|ibuprofen|acetaminophen|metformin|lisinopril|amoxicillin"
    r"|omeprazole|atorvastatin|metoprolol|amlodipine|losartan|gabapentin"
    r"|hydrochlorothiazide|prednisone|warfarin|insulin|heparin"
    r")\b",
    re.IGNORECASE,
)

# Dosage patterns: e.g. "500mg", "10 mL", "0.5mcg", "100 units"
_DOSAGE_PATTERNS = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|mL|L|units?|IU|cc|mmol|mEq))\b",
    re.IGNORECASE,
)

# Common condition / diagnosis patterns
_CONDITION_PATTERNS = re.compile(
    r"\b("
    r"diabetes(?:\s+mellitus)?|hypertension|hyperlipidemia|pneumonia"
    r"|asthma|COPD|CHF|heart\s+failure|stroke|sepsis|anemia|arthritis"
    r"|depression|anxiety|infection|fracture|cancer|tumor|inflammation"
    r"|edema|neuropathy|fibrillation|embolism|thrombosis"
    r")\b",
    re.IGNORECASE,
)

# Procedure patterns
_PROCEDURE_PATTERNS = re.compile(
    r"\b("
    r"biopsy|MRI|CT\s*scan|X-?ray|ultrasound|echocardiogram|endoscopy"
    r"|colonoscopy|surgery|transplant|catheterization|dialysis"
    r"|intubation|ventilation|transfusion|excision|resection"
    r")\b",
    re.IGNORECASE,
)

# Anatomy patterns
_ANATOMY_PATTERNS = re.compile(
    r"\b("
    r"heart|lung|liver|kidney|brain|spine|abdomen|thorax|pelvis"
    r"|femur|tibia|cranium|pancreas|spleen|colon|esophagus"
    r"|trachea|bronchus|aorta|ventricle|atrium|retina|cornea"
    r")\b",
    re.IGNORECASE,
)

# PII patterns for de-identification
_MRN_PATTERN = re.compile(r"\b(?:MRN[:#\s]*)?(\d{6,10})\b")
_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
)
_NAME_PATTERN = re.compile(
    r"\b(?:(?:Mr|Mrs|Ms|Dr|Patient)\.?\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)
_ADDRESS_PATTERN = re.compile(
    r"\b(\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*\s+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct)\.?)\b"
)

# Section header patterns for clinical notes
_SECTION_HEADERS = {
    "chief_complaint": re.compile(
        r"(?:CC|Chief\s+Complaint|Reason\s+for\s+Visit)\s*[:;]\s*", re.IGNORECASE
    ),
    "history": re.compile(
        r"(?:HPI|History\s+of\s+Present\s+Illness|History)\s*[:;]\s*", re.IGNORECASE
    ),
    "assessment": re.compile(
        r"(?:Assessment|Impression|Diagnosis|Dx)\s*[:;]\s*", re.IGNORECASE
    ),
    "plan": re.compile(
        r"(?:Plan|Treatment\s+Plan|Recommendations)\s*[:;]\s*", re.IGNORECASE
    ),
}


class MedicalNLPService:
    """NLP service for clinical text processing."""

    @staticmethod
    def extract_medical_terms(text: str) -> list[dict[str, Any]]:
        """Extract medical terms from text with type classification and positions.

        Returns a list of dicts with keys: term, type, position ([start, end]).
        Types: drug, condition, procedure, anatomy, dosage.
        """
        results: list[dict[str, Any]] = []
        seen_spans: set[tuple[int, int]] = set()

        pattern_map: list[tuple[str, re.Pattern[str]]] = [
            ("drug", _DRUG_PATTERNS),
            ("dosage", _DOSAGE_PATTERNS),
            ("condition", _CONDITION_PATTERNS),
            ("procedure", _PROCEDURE_PATTERNS),
            ("anatomy", _ANATOMY_PATTERNS),
        ]

        for term_type, pattern in pattern_map:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                results.append({
                    "term": match.group(0),
                    "type": term_type,
                    "position": [span[0], span[1]],
                })

        # Sort by position in text
        results.sort(key=lambda r: r["position"][0])
        return results

    @staticmethod
    def structure_clinical_note(transcript: str) -> dict[str, str]:
        """Parse a clinical transcript into structured SOAP-style sections.

        Recognised section headers: CC:/Chief Complaint:, HPI:/History:,
        Assessment:, Plan:.  Unrecognised leading text is placed in
        ``chief_complaint`` as a fallback.

        Returns dict with keys: chief_complaint, history, assessment, plan.
        """
        sections: dict[str, str] = {
            "chief_complaint": "",
            "history": "",
            "assessment": "",
            "plan": "",
        }

        # Collect all header positions
        markers: list[tuple[int, str]] = []
        for key, pattern in _SECTION_HEADERS.items():
            for m in pattern.finditer(transcript):
                markers.append((m.end(), key))

        if not markers:
            # No recognised headers — put everything in chief_complaint
            sections["chief_complaint"] = transcript.strip()
            return sections

        markers.sort(key=lambda x: x[0])

        # Text before the first marker goes into chief_complaint if marker isn't CC
        first_start = markers[0][0]
        # Find the start of the header itself (search backwards for header match)
        header_match = None
        for pattern in _SECTION_HEADERS.values():
            m = pattern.search(transcript)
            if m and m.end() == first_start:
                header_match = m
                break

        preamble_end = header_match.start() if header_match else first_start
        preamble = transcript[:preamble_end].strip()
        if preamble and markers[0][1] != "chief_complaint":
            sections["chief_complaint"] = preamble

        # Fill sections from markers
        for i, (start, key) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(transcript)
            # Find the actual header start for the next marker to exclude it
            if i + 1 < len(markers):
                for pattern in _SECTION_HEADERS.values():
                    for m in pattern.finditer(transcript):
                        if m.end() == markers[i + 1][0]:
                            end = m.start()
                            break
            content = transcript[start:end].strip()
            if sections[key]:
                sections[key] += " " + content
            else:
                sections[key] = content

        return sections

    @staticmethod
    def deidentify_text(text: str) -> str:
        """Redact PHI / PII from clinical text for HIPAA compliance.

        Redacts: patient names (preceded by title), dates, MRN numbers,
        and street addresses.

        Returns the redacted text with ``[REDACTED]`` placeholders.
        """
        result = text

        # Redact names (with title prefix)
        result = _NAME_PATTERN.sub(lambda m: m.group(0).replace(m.group(1), "[REDACTED]"), result)

        # Redact MRN numbers
        result = re.sub(r"\bMRN[:#\s]*\d{6,10}\b", "MRN [REDACTED]", result)

        # Redact dates
        result = _DATE_PATTERN.sub("[REDACTED]", result)

        # Redact addresses
        result = _ADDRESS_PATTERN.sub("[REDACTED]", result)

        return result
