"""Transform Presets — curated chains for common audio and video workflows."""

from __future__ import annotations

AUDIO_PRESETS: dict[str, dict] = {
    "podcast_cleanup": {
        "description": "Full podcast cleanup: denoise, remove silence, normalize loudness to -14 LUFS, voice EQ.",
        "operations": [
            {"op": "denoise", "method": "spectral_gating"},
            {"op": "silence_remove"},
            {"op": "loudness", "target_lufs": -14},
            {"op": "eq", "preset": "voice"},
        ],
    },
    "voice_enhancement": {
        "description": "Enhance voice clarity: denoise, normalize loudness to -14 LUFS, voice EQ.",
        "operations": [
            {"op": "denoise", "method": "spectral_gating"},
            {"op": "loudness", "target_lufs": -14},
            {"op": "eq", "preset": "voice"},
        ],
    },
    "music_master": {
        "description": "Basic music mastering: normalize loudness to -14 LUFS, music EQ.",
        "operations": [
            {"op": "loudness", "target_lufs": -14},
            {"op": "eq", "preset": "music"},
        ],
    },
    "interview_cleanup": {
        "description": "Interview cleanup: denoise, remove silence, normalize loudness to -16 LUFS, voice EQ.",
        "operations": [
            {"op": "denoise", "method": "spectral_gating"},
            {"op": "silence_remove"},
            {"op": "loudness", "target_lufs": -16},
            {"op": "eq", "preset": "voice"},
        ],
    },
}

VIDEO_PRESETS: dict[str, dict] = {
    "social_media": {
        "description": "Optimize for social media: square crop, high contrast color grade, subtitle burn.",
        "operations": [
            {"op": "auto_crop", "aspect": "1:1"},
            {"op": "color_grade", "preset": "high_contrast"},
            {"op": "subtitle", "text": "", "position": "bottom"},
        ],
    },
    "cinematic": {
        "description": "Cinematic look: cinematic color grade, 21:9 ultra-wide crop.",
        "operations": [
            {"op": "color_grade", "preset": "cinematic"},
            {"op": "auto_crop", "aspect": "21:9"},
        ],
    },
    "thumbnail": {
        "description": "Thumbnail generation: smart crop to target size, high contrast grading.",
        "operations": [
            {"op": "smart_crop", "target_width": 320, "target_height": 180, "method": "center_of_mass"},
            {"op": "color_grade", "preset": "high_contrast"},
        ],
    },
}


def list_all_presets() -> dict:
    """Return all presets grouped by category with descriptions."""
    return {
        "audio": {
            name: {
                "description": preset["description"],
                "operations": preset["operations"],
            }
            for name, preset in AUDIO_PRESETS.items()
        },
        "video": {
            name: {
                "description": preset["description"],
                "operations": preset["operations"],
            }
            for name, preset in VIDEO_PRESETS.items()
        },
    }
