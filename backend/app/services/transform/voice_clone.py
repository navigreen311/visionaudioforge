"""Voice cloning service — stub implementation.

Real voice cloning requires Coqui TTS or ElevenLabs API.
"""

from __future__ import annotations

import numpy as np


class VoiceCloneService:
    """Stub voice cloning service with consent management."""

    def clone_voice(
        self,
        reference_audio: np.ndarray,
        sr: int,
        text: str,
    ) -> dict:
        """Clone a voice from reference audio and synthesize text.

        V1 stub: returns None audio with instructions for setup.
        """
        return {
            "audio": None,
            "note": (
                "Voice cloning requires Coqui TTS or ElevenLabs API. "
                "Set VOICE_CLONE_API_KEY in env. Reference audio would be "
                "used to create a voice profile."
            ),
        }

    def check_consent(
        self,
        user_id: str,
        voice_owner_id: str,
    ) -> dict:
        """Check whether consent has been given for voice cloning.

        Always returns consent_given=False until a real consent system is wired.
        """
        return {
            "consent_given": False,
            "note": (
                "Voice cloning requires explicit consent from the voice owner. "
                "Consent management is not yet implemented. "
                f"User '{user_id}' must obtain permission from voice owner "
                f"'{voice_owner_id}' before cloning."
            ),
        }
