"""Security-related Pydantic schemas for sessions, 2FA, password, and login history."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    id: UUID
    device: str
    browser: str
    location: str
    ip_address: str
    last_active: datetime
    is_current: bool

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------

class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    enabled_at: datetime | None = None


class TwoFactorEnableRequest(BaseModel):
    """Verify the TOTP code after scanning the QR."""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TwoFactorEnableResponse(BaseModel):
    qr_code_url: str
    secret: str
    message: str


class TwoFactorVerifyResponse(BaseModel):
    enabled: bool
    message: str
    backup_codes: list[str] = []


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class ChangePasswordResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Login History
# ---------------------------------------------------------------------------

class LoginHistoryEntry(BaseModel):
    id: UUID
    timestamp: datetime
    device: str
    browser: str
    ip_address: str
    location: str
    status: str  # "success" | "failed"

    model_config = {"from_attributes": True}


class LoginHistoryResponse(BaseModel):
    entries: list[LoginHistoryEntry]
    total: int
