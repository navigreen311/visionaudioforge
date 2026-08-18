"""Account security state — sessions, login history, and two-factor enrolment.

All three were module-level dicts, which made them wrong in two ways at once.
They did not survive a restart, and they were not per-user: a single
``_2fa_enabled`` boolean meant one account enabling 2FA reported it as enabled
for everybody, and one shared session list meant every user saw the same
devices. Security state that lies about whose it is, is worse than absent.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class LoginStatus(str, enum.Enum):
    success = "success"
    failed = "failed"


class UserSession(UUIDMixin, TimestampMixin, Base):
    """One active sign-in for one user."""

    __tablename__ = "user_sessions"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    device = Column(String(200), nullable=False, default="Unknown device")
    browser = Column(String(200), nullable=False, default="Unknown browser")
    location = Column(String(200), nullable=False, default="Unknown")
    ip_address = Column(String(64), nullable=False, default="0.0.0.0")
    last_active = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Marks the session the current request is authenticated with, so
    # "revoke all other sessions" can spare it.
    is_current = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "last_active"),
    )


class LoginEvent(UUIDMixin, Base):
    """One sign-in attempt, successful or not. Append-only.

    Failed attempts are the point: a history that only records successes cannot
    show an account being probed.
    """

    __tablename__ = "login_events"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    device = Column(String(200), nullable=False, default="Unknown device")
    browser = Column(String(200), nullable=False, default="Unknown browser")
    ip_address = Column(String(64), nullable=False, default="0.0.0.0")
    location = Column(String(200), nullable=False, default="Unknown")
    status = Column(Enum(LoginStatus), nullable=False, default=LoginStatus.success)

    __table_args__ = (
        Index("ix_login_events_user_timestamp", "user_id", "timestamp"),
    )


class UserTwoFactor(UUIDMixin, TimestampMixin, Base):
    """Per-user two-factor enrolment.

    Kept in its own table rather than as columns on ``users`` so the TOTP secret
    is not loaded on every ordinary user lookup.
    """

    __tablename__ = "user_two_factor"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    enabled = Column(Boolean, nullable=False, default=False)
    # Present once setup has begun, before verification completes.
    secret = Column(String(64), nullable=True)
    enabled_at = Column(DateTime(timezone=True), nullable=True)
