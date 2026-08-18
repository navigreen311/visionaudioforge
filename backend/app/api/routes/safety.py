"""Safety & Privacy API routes — scanning, redaction, watermarking,
plate blur, voice anonymization, policy engine, provenance, and compliance."""

from __future__ import annotations

import base64
import io
import struct
import wave

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.database import get_async_session
from app.schemas.safety import (
    ContentSafetyResult,
    RedactRequest,
    RedactionResult,
    ReportRequest,
    SafetyReport,
    SafetyScanResult,
)
from app.services.safety.scanner import SafetyScanner
from app.services.safety.content_safety import ContentSafetyChecker
from app.services.safety.plate_blur import PlateBlurService
from app.services.safety.voice_anon import VoiceAnonymizer
from app.services.safety.policy_engine import PolicyEngine
from app.services.safety.provenance import ProvenanceTracker
from app.services.safety.compliance import ComplianceManager

router = APIRouter(prefix="/api/safety", tags=["safety"])

_scanner = SafetyScanner()
_content_checker = ContentSafetyChecker()
_plate_blur = PlateBlurService()
_voice_anon = VoiceAnonymizer()
_policy_engine = PolicyEngine()
_provenance = ProvenanceTracker()
_compliance = ComplianceManager()

# In-memory scan result store (simple dict keyed by auto-incrementing id)
_scan_store: dict[str, dict] = {}
_scan_counter: int = 0


def _next_scan_id() -> str:
    global _scan_counter
    _scan_counter += 1
    return str(_scan_counter)


def _decode_image(data: bytes) -> np.ndarray:
    """Decode uploaded image bytes into a BGR numpy array."""
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image file")
    return image


def _encode_image_base64(image: np.ndarray) -> str:
    """Encode a BGR numpy array as a base64 PNG string."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


@router.post("/scan", response_model=SafetyScanResult)
async def safety_scan(
    file: UploadFile = File(None),
    scan_type: str = Form("image"),
    text: str = Form(None),
):
    """Scan an uploaded file or text for safety / privacy concerns."""
    if scan_type == "image":
        if file is None:
            raise HTTPException(status_code=422, detail="File required for image scan")
        data = await file.read()
        image = _decode_image(data)
        result = await _scanner.scan_image(image)

    elif scan_type == "text":
        if text is None and file is not None:
            text = (await file.read()).decode("utf-8", errors="replace")
        if not text:
            raise HTTPException(status_code=422, detail="Text required for text scan")
        pii = _scanner.detect_text_pii(text)
        risk = min(len(pii) * 0.15, 1.0)
        recs = []
        if pii:
            recs.append("PII detected — consider redacting before sharing.")
        result = {
            "faces_detected": 0,
            "face_locations": [],
            "pii_found": pii,
            "risk_score": risk,
            "recommendations": recs,
        }

    elif scan_type == "audio":
        if text is None and file is not None:
            text = (await file.read()).decode("utf-8", errors="replace")
        if not text:
            raise HTTPException(status_code=400, detail="Transcript text required for audio scan")
        pii = await _scanner.scan_audio_pii(text)
        risk = min(len(pii) * 0.15, 1.0)
        recs = []
        if pii:
            recs.append("PII detected in audio transcript — consider redacting.")
        result = {
            "faces_detected": 0,
            "face_locations": [],
            "pii_found": pii,
            "risk_score": risk,
            "recommendations": recs,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scan_type: {scan_type}")

    # Store for later report aggregation
    scan_id = _next_scan_id()
    _scan_store[scan_id] = result

    return result


@router.post("/blur-faces")
async def blur_faces(file: UploadFile = File(...)):
    """Detect and blur faces in an uploaded image, return base64 PNG."""
    data = await file.read()
    image = _decode_image(data)
    blurred = await _scanner.blur_faces(image)
    return {"image": _encode_image_base64(blurred)}


@router.post("/redact", response_model=RedactionResult)
async def redact_pii(body: RedactRequest):
    """Redact PII from the provided text."""
    result = await _scanner.redact_pii(body.text)
    return result


@router.post("/watermark")
async def watermark_image(
    file: UploadFile = File(...),
    text: str = Form("VAF-GENERATED"),
):
    """Add a text watermark to an uploaded image, return base64 PNG."""
    data = await file.read()
    image = _decode_image(data)
    watermarked = await _content_checker.watermark_image(image, text=text)
    return {"image": _encode_image_base64(watermarked)}


@router.post("/report", response_model=SafetyReport)
async def safety_report(body: ReportRequest):
    """Generate an aggregated safety report from previous scan results."""
    results: list[dict] = []
    for sid in body.scan_ids:
        if sid in _scan_store:
            results.append(_scan_store[sid])

    if not results:
        # If no valid IDs, return empty report
        return {
            "total_scans": 0,
            "faces_found": 0,
            "pii_instances": 0,
            "avg_risk_score": 0.0,
            "recommendations": [],
        }

    report = await _scanner.generate_safety_report(results)
    return report


# ------------------------------------------------------------------
# Plate blur
# ------------------------------------------------------------------


@router.post("/blur-plates")
async def blur_plates(file: UploadFile = File(...)):
    """Detect and blur license plates in an uploaded image."""
    data = await file.read()
    image = _decode_image(data)
    blurred = _plate_blur.blur_plates(image)
    return {"image": _encode_image_base64(blurred)}


# ------------------------------------------------------------------
# Voice anonymization
# ------------------------------------------------------------------


def _decode_wav(data: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV bytes into (float64 audio array, sample_rate)."""
    buf = io.BytesIO(data)
    with wave.open(buf, "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64) / 32768.0
    else:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) / 128.0 - 1.0

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return samples, sr


def _encode_wav(audio: np.ndarray, sr: int) -> bytes:
    """Encode float64 audio array to WAV bytes."""
    buf = io.BytesIO()
    clipped = np.clip(audio, -1.0, 1.0)
    int_samples = (clipped * 32767).astype(np.int16)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())
    return buf.getvalue()


@router.post("/anonymize-voice")
async def anonymize_voice(
    file: UploadFile = File(...),
    method: str = Form("pitch"),
):
    """Anonymize voice in uploaded WAV audio, return base64 WAV."""
    data = await file.read()
    try:
        audio, sr = _decode_wav(data)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode WAV audio")

    result = _voice_anon.anonymize(audio, sr, method=method)
    wav_bytes = _encode_wav(result, sr)
    return {"audio": base64.b64encode(wav_bytes).decode("utf-8")}


# ------------------------------------------------------------------
# Policy engine
# ------------------------------------------------------------------


class PolicyEvaluateRequest(BaseModel):
    scan_result: dict = Field(..., description="Scan result to evaluate")
    policy_name: str = Field("strict_pii", description="Built-in policy name")


class ExportCheckRequest(BaseModel):
    asset_id: str = Field(..., description="Asset ID to check")
    policy: str = Field("strict_pii", description="Policy name")


@router.post("/policy/evaluate")
async def evaluate_policy(body: PolicyEvaluateRequest):
    """Evaluate a scan result against a named policy."""
    from app.services.safety.policy_engine import BUILT_IN_POLICIES

    policy = BUILT_IN_POLICIES.get(body.policy_name)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Unknown policy: {body.policy_name}")
    return _policy_engine.evaluate_policy(policy, body.scan_result)


@router.post("/policy/check-export")
async def check_export(body: ExportCheckRequest):
    """Check whether an asset export is allowed under a policy."""
    # In a real system we'd load the scan result for the asset; here we
    # accept the policy name and return based on an empty scan (allowed).
    scan_result: dict = _scan_store.get(body.asset_id, {
        "faces_detected": 0, "pii_found": [], "risk_score": 0.0,
    })
    return _policy_engine.check_export_allowed(scan_result, body.policy)


# ------------------------------------------------------------------
# Compliance
# ------------------------------------------------------------------


@router.get("/compliance/{pack}")
async def check_compliance(pack: str = Path(...)):
    """Check workspace compliance against a pack (hipaa, gdpr, soc2)."""
    try:
        return _compliance.check_compliance(None, "default", pack)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/compliance/{pack}/report")
async def compliance_report(pack: str = Path(...)):
    """Generate a compliance report for the given pack."""
    try:
        return _compliance.generate_compliance_report(None, "default", pack)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class LegalHoldRequest(BaseModel):
    asset_ids: list[str] = Field(..., description="Asset IDs to hold")
    reason: str = Field(..., description="Reason for hold")


@router.post("/legal-hold")
async def legal_hold(body: LegalHoldRequest):
    """Place a legal hold on assets."""
    return _compliance.legal_hold(None, body.asset_ids, body.reason, "system")


# ------------------------------------------------------------------
# Provenance
# ------------------------------------------------------------------


@router.get("/provenance/{asset_id}")
async def get_provenance(
    asset_id: str = Path(...),
    workspace_id: str | None = Query(
        None, description="Scope the chain to one workspace"
    ),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the provenance chain for an asset."""
    chain = await _provenance.get_provenance_chain(db, asset_id, workspace_id)
    return {"asset_id": asset_id, "chain": chain}
