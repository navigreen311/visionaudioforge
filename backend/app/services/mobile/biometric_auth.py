"""Biometric authentication stub.

Biometric verification (Face ID / Touch ID / Fingerprint) is handled
entirely by the mobile OS.  The backend simply validates the JWT token
issued after the device completes biometric verification.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.security import decode_token

logger = logging.getLogger(__name__)


class BiometricAuthService:
    """Backend stubs for biometric authentication flow."""

    @staticmethod
    def register_biometric_stub(
        user_id: str,
        biometric_type: str,
    ) -> dict[str, Any]:
        """Register biometric capability for a user.

        Args:
            biometric_type: 'face_id', 'touch_id', 'fingerprint'

        This is a stub — biometric enrolment is handled by the mobile OS.
        The backend only needs to know the user has opted in.
        """
        logger.info(
            "Biometric registration stub: user=%s type=%s", user_id, biometric_type,
        )
        return {
            "registered": True,
            "note": (
                "Biometric auth handled by mobile OS (Face ID / Touch ID / Fingerprint). "
                "Backend validates the JWT token issued after successful biometric "
                "verification on device."
            ),
        }

    @staticmethod
    def verify_biometric_token(token: str) -> dict[str, Any]:
        """Verify a JWT token issued after device-side biometric check.

        V1: standard JWT verification — the biometric check itself is
        device-side only.
        """
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            return {"valid": True, "user_id": user_id}
        except Exception:
            logger.warning("Biometric token verification failed")
            return {"valid": False, "user_id": None}
