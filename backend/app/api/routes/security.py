"""Security routes: sessions, 2FA, password change, login history."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.security import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginHistoryEntry,
    LoginHistoryResponse,
    SessionListResponse,
    SessionResponse,
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorEnableResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyResponse,
)

router = APIRouter(
    prefix="/api/security",
    tags=["security"],
)

# ---------------------------------------------------------------------------
# In-memory mock stores (replace with DB in production)
# ---------------------------------------------------------------------------
_now = datetime.now(timezone.utc)

_mock_sessions: list[dict[str, object]] = [
    {
        "id": "a1b2c3d4-0001-4000-a000-000000000001",
        "device": "Windows 11",
        "browser": "Chrome 124",
        "location": "New York, US",
        "ip_address": "192.168.1.10",
        "last_active": _now.isoformat(),
        "is_current": True,
    },
    {
        "id": "a1b2c3d4-0002-4000-a000-000000000002",
        "device": "macOS Sonoma",
        "browser": "Safari 17",
        "location": "San Francisco, US",
        "ip_address": "10.0.0.42",
        "last_active": (_now - timedelta(hours=3)).isoformat(),
        "is_current": False,
    },
    {
        "id": "a1b2c3d4-0003-4000-a000-000000000003",
        "device": "iPhone 15",
        "browser": "Mobile Safari",
        "location": "Chicago, US",
        "ip_address": "172.16.0.5",
        "last_active": (_now - timedelta(days=1)).isoformat(),
        "is_current": False,
    },
]

_mock_login_history: list[dict[str, object]] = [
    {
        "id": str(uuid4()),
        "timestamp": (_now - timedelta(minutes=i * 47 + 3)).isoformat(),
        "device": ["Windows 11", "macOS Sonoma", "iPhone 15", "Linux Desktop"][i % 4],
        "browser": ["Chrome 124", "Safari 17", "Mobile Safari", "Firefox 125"][i % 4],
        "ip_address": f"192.168.1.{10 + i}",
        "location": ["New York, US", "San Francisco, US", "Chicago, US", "London, UK"][i % 4],
        "status": "failed" if i in (3, 7, 12) else "success",
    }
    for i in range(20)
]

_2fa_enabled = False


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: User = Depends(get_current_user)):
    """Return all active sessions for the current user."""
    sessions = [SessionResponse(**s) for s in _mock_sessions]  # type: ignore[arg-type]
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Revoke a specific session by ID."""
    global _mock_sessions
    original_len = len(_mock_sessions)
    _mock_sessions = [s for s in _mock_sessions if s["id"] != session_id]
    if len(_mock_sessions) == original_len:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked successfully"}


@router.delete("/sessions")
async def revoke_all_other_sessions(current_user: User = Depends(get_current_user)):
    """Revoke all sessions except the current one."""
    global _mock_sessions
    _mock_sessions = [s for s in _mock_sessions if s.get("is_current")]
    return {"message": "All other sessions revoked"}


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(current_user: User = Depends(get_current_user)):
    """Return the current 2FA status."""
    return TwoFactorStatusResponse(
        enabled=_2fa_enabled,
        enabled_at=_now if _2fa_enabled else None,
    )


@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa_setup(current_user: User = Depends(get_current_user)):
    """Generate a new TOTP secret and QR code URL for 2FA setup."""
    secret = "JBSWY3DPEHPK3PXP"  # Placeholder — use pyotp in production
    qr_url = f"otpauth://totp/VisionAudioForge:{current_user.email}?secret={secret}&issuer=VisionAudioForge"
    return TwoFactorEnableResponse(
        qr_code_url=qr_url,
        secret=secret,
        message="Scan the QR code with your authenticator app, then verify with a code.",
    )


@router.post("/2fa/verify", response_model=TwoFactorVerifyResponse)
async def verify_2fa(body: TwoFactorEnableRequest, current_user: User = Depends(get_current_user)):
    """Verify the TOTP code and activate 2FA."""
    global _2fa_enabled
    # Placeholder validation — accept any 6-digit code for now
    if len(body.code) != 6 or not body.code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid verification code")
    _2fa_enabled = True
    return TwoFactorVerifyResponse(
        enabled=True,
        message="Two-factor authentication enabled successfully.",
        backup_codes=["ABC12-DEF34", "GHI56-JKL78", "MNO90-PQR12", "STU34-VWX56"],
    )


@router.post("/2fa/disable")
async def disable_2fa(body: TwoFactorDisableRequest, current_user: User = Depends(get_current_user)):
    """Disable 2FA after verifying the user's password."""
    global _2fa_enabled
    # Placeholder password check
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required")
    _2fa_enabled = False
    return {"message": "Two-factor authentication disabled", "enabled": False}


# ---------------------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------------------


@router.post("/password", response_model=ChangePasswordResponse)
async def change_password(body: ChangePasswordRequest, current_user: User = Depends(get_current_user)):
    """Change the current user's password."""
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from current")
    # In production: verify current_password hash, then update
    return ChangePasswordResponse(message="Password changed successfully")


# ---------------------------------------------------------------------------
# Login History
# ---------------------------------------------------------------------------


@router.get("/login-history", response_model=LoginHistoryResponse)
async def get_login_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """Return the most recent login events."""
    entries = [LoginHistoryEntry(**e) for e in _mock_login_history[:limit]]  # type: ignore[arg-type]
    return LoginHistoryResponse(entries=entries, total=len(_mock_login_history))
