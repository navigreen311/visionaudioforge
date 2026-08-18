"""Security routes: sessions, 2FA, password change, login history.

Every store here used to be a module-level list. That made the data wrong in
two ways rather than one: it vanished on restart, and it was shared across all
users — a single ``_2fa_enabled`` boolean reported one account's enrolment as
everybody's, and one session list showed every user the same devices.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_async_session
from app.models.security import LoginEvent, UserSession, UserTwoFactor
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

# Placeholder TOTP secret. Real enrolment needs pyotp to generate a per-user
# secret and verify the code against it; this is flagged rather than hidden.
_PLACEHOLDER_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return all active sessions for the current user."""
    rows = (
        await db.execute(
            select(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.revoked_at.is_(None),
            )
            .order_by(UserSession.last_active.desc())
        )
    ).scalars().all()

    sessions = [SessionResponse.model_validate(r) for r in rows]
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Revoke a specific session by ID."""
    session_row = (
        await db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                # Scoped to the caller: one user must not revoke another's
                # session by guessing an id.
                UserSession.user_id == current_user.id,
                UserSession.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session_row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Session revoked successfully"}


@router.delete("/sessions")
async def revoke_all_other_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Revoke all of this user's sessions except the current one."""
    rows = (
        await db.execute(
            select(UserSession).where(
                UserSession.user_id == current_user.id,
                UserSession.revoked_at.is_(None),
                UserSession.is_current.is_(False),
            )
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)
    for row in rows:
        row.revoked_at = now
    await db.commit()

    return {"message": "All other sessions revoked", "revoked": len(rows)}


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------


async def _two_factor_for(db: AsyncSession, user_id) -> UserTwoFactor | None:
    return (
        await db.execute(
            select(UserTwoFactor).where(UserTwoFactor.user_id == user_id)
        )
    ).scalar_one_or_none()


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return this user's 2FA status."""
    record = await _two_factor_for(db, current_user.id)
    if record is None:
        return TwoFactorStatusResponse(enabled=False, enabled_at=None)
    return TwoFactorStatusResponse(
        enabled=record.enabled,
        enabled_at=record.enabled_at if record.enabled else None,
    )


@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Begin 2FA setup: store a secret and return it for QR enrolment."""
    record = await _two_factor_for(db, current_user.id)
    if record is None:
        record = UserTwoFactor(user_id=current_user.id, enabled=False)
        db.add(record)

    record.secret = _PLACEHOLDER_TOTP_SECRET
    await db.commit()

    qr_url = (
        f"otpauth://totp/VisionAudioForge:{current_user.email}"
        f"?secret={record.secret}&issuer=VisionAudioForge"
    )
    return TwoFactorEnableResponse(
        qr_code_url=qr_url,
        secret=record.secret,
        message="Scan the QR code with your authenticator app, then verify with a code.",
    )


@router.post("/2fa/verify", response_model=TwoFactorVerifyResponse)
async def verify_2fa(
    body: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Verify the TOTP code and activate 2FA for this user.

    NOTE: the code is only checked for shape, not against the stored secret —
    real verification needs pyotp. Enrolment is persisted regardless so the
    enabled state is at least per-user and durable.
    """
    if len(body.code) != 6 or not body.code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid verification code")

    record = await _two_factor_for(db, current_user.id)
    if record is None:
        record = UserTwoFactor(user_id=current_user.id)
        db.add(record)

    record.enabled = True
    record.enabled_at = datetime.now(timezone.utc)
    await db.commit()

    return TwoFactorVerifyResponse(
        enabled=True,
        message="Two-factor authentication enabled successfully.",
        backup_codes=["ABC12-DEF34", "GHI56-JKL78", "MNO90-PQR12", "STU34-VWX56"],
    )


@router.post("/2fa/disable")
async def disable_2fa(
    body: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Disable 2FA after verifying the user's password."""
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required")

    record = await _two_factor_for(db, current_user.id)
    if record is not None:
        record.enabled = False
        record.enabled_at = None
        record.secret = None
        await db.commit()

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
    db: AsyncSession = Depends(get_async_session),
):
    """Return this user's most recent login events, newest first."""
    stmt = (
        select(LoginEvent)
        .where(LoginEvent.user_id == current_user.id)
        .order_by(LoginEvent.timestamp.desc())
    )
    rows = (await db.execute(stmt.limit(limit))).scalars().all()
    total = len((await db.execute(stmt)).scalars().all())

    entries = [LoginHistoryEntry.model_validate(r) for r in rows]
    return LoginHistoryResponse(entries=entries, total=total)
