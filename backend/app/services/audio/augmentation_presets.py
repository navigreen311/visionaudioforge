"""Pre-defined augmentation pipeline presets.

Each preset is a list of augmentation steps suitable for
:meth:`AudioAugmenter.apply_pipeline`.
"""

from __future__ import annotations

PRESETS: dict[str, list[dict]] = {
    "speech_robust": [
        {"type": "noise", "probability": 0.7, "params": {"noise_type": "white", "snr_db": 15}},
        {"type": "stretch", "probability": 0.5, "params": {"rate": 0.9}},
        {"type": "stretch", "probability": 0.5, "params": {"rate": 1.1}},
        {"type": "pitch", "probability": 0.3, "params": {"n_steps": -2}},
        {"type": "pitch", "probability": 0.3, "params": {"n_steps": 2}},
    ],
    "music_robust": [
        {"type": "noise", "probability": 0.5, "params": {"noise_type": "white", "snr_db": 20}},
        {"type": "stretch", "probability": 0.6, "params": {"rate": 0.8}},
        {"type": "stretch", "probability": 0.6, "params": {"rate": 1.2}},
        {"type": "pitch", "probability": 0.4, "params": {"n_steps": -3}},
        {"type": "pitch", "probability": 0.4, "params": {"n_steps": 3}},
    ],
    "environmental": [
        {"type": "noise", "probability": 0.8, "params": {"noise_type": "white", "snr_db": 10}},
        {"type": "shift", "probability": 0.5, "params": {"shift_ms": -200}},
        {"type": "shift", "probability": 0.5, "params": {"shift_ms": 200}},
    ],
    "light": [
        {"type": "noise", "probability": 0.3, "params": {"noise_type": "white", "snr_db": 25}},
        {"type": "pitch", "probability": 0.2, "params": {"n_steps": -1}},
        {"type": "pitch", "probability": 0.2, "params": {"n_steps": 1}},
    ],
    "heavy": [
        {"type": "noise", "probability": 0.9, "params": {"noise_type": "white", "snr_db": 5}},
        {"type": "stretch", "probability": 0.7, "params": {"rate": 0.7}},
        {"type": "stretch", "probability": 0.7, "params": {"rate": 1.3}},
        {"type": "pitch", "probability": 0.6, "params": {"n_steps": -5}},
        {"type": "pitch", "probability": 0.6, "params": {"n_steps": 5}},
        {"type": "shift", "probability": 0.5, "params": {"shift_ms": -500}},
        {"type": "shift", "probability": 0.5, "params": {"shift_ms": 500}},
    ],
}
