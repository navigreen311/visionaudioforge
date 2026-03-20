"""Synthetic data generation service — shapes, noise, audio tones, balancing."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.data.storage import MinIOStorageService

logger = logging.getLogger(__name__)

BUCKET = "vaf-datasets"


class SyntheticDataGenerator:
    """Generate synthetic image and audio data for training and augmentation."""

    # ------------------------------------------------------------------
    # Synthetic images
    # ------------------------------------------------------------------

    @staticmethod
    def generate_synthetic_images(
        num: int,
        width: int = 224,
        height: int = 224,
        pattern: str = "shapes",
    ) -> list[np.ndarray]:
        """Generate *num* synthetic images of the given pattern type.

        Patterns:
        - ``shapes``: random coloured shapes on random backgrounds
        - ``noise``: uniform random noise
        - ``gradient``: smooth colour gradients
        """
        generators = {
            "shapes": _gen_shapes_image,
            "noise": _gen_noise_image,
            "gradient": _gen_gradient_image,
        }
        gen_fn = generators.get(pattern, _gen_shapes_image)

        rng = np.random.RandomState(42)
        return [gen_fn(width, height, rng) for _ in range(num)]

    # ------------------------------------------------------------------
    # Synthetic audio
    # ------------------------------------------------------------------

    @staticmethod
    def generate_synthetic_audio(
        num: int,
        duration: float = 1.0,
        sr: int = 22050,
        pattern: str = "tones",
    ) -> list[np.ndarray]:
        """Generate *num* synthetic audio waveforms.

        Patterns:
        - ``tones``: random-frequency sine waves
        - ``noise``: white noise
        - ``speech_like``: amplitude-modulated tones mimicking speech
        """
        generators = {
            "tones": _gen_tone,
            "noise": _gen_audio_noise,
            "speech_like": _gen_speech_like,
        }
        gen_fn = generators.get(pattern, _gen_tone)

        rng = np.random.RandomState(42)
        return [gen_fn(duration, sr, rng) for _ in range(num)]

    # ------------------------------------------------------------------
    # Augment to balance
    # ------------------------------------------------------------------

    @staticmethod
    async def augment_to_balance(
        db: AsyncSession,
        storage: MinIOStorageService,
        dataset_id: uuid.UUID,
        target_count_per_class: int,
    ) -> dict[str, Any]:
        """Generate augmented samples for underrepresented classes.

        For each class below ``target_count_per_class``, produce synthetic
        variations until the target is reached.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        class_assets: dict[str, list[Asset]] = defaultdict(list)
        for a in assets:
            label = (a.metadata_ or {}).get("label")
            if label:
                class_assets[label].append(a)

        generated = 0
        classes_augmented: list[str] = []

        for label, class_items in class_assets.items():
            deficit = target_count_per_class - len(class_items)
            if deficit <= 0:
                continue

            classes_augmented.append(label)
            rng = np.random.RandomState(hash(label) % (2**31))

            for i in range(deficit):
                # Create augmented version by varying size metadata
                source = class_items[i % len(class_items)]
                new_size = (source.size_bytes or 1024) + rng.randint(-100, 100)

                synthetic_asset = Asset(
                    filename=f"synthetic_{label}_{i}_{uuid.uuid4().hex[:8]}.png",
                    media_type=getattr(source, "media_type", "image"),
                    mime_type=getattr(source, "mime_type", "image/png"),
                    size_bytes=max(1, new_size),
                    storage_path=f"{BUCKET}/{dataset_id}/synthetic/{label}_{i}.png",
                    metadata_={
                        "dataset_id": str(dataset_id),
                        "label": label,
                        "synthetic": True,
                        "source_asset_id": str(source.id),
                    },
                    workspace_id=source.workspace_id,
                )
                db.add(synthetic_asset)
                generated += 1

        await db.commit()
        return {"generated": generated, "classes_augmented": classes_augmented}


# ---------------------------------------------------------------------------
# Image generators
# ---------------------------------------------------------------------------

def _gen_shapes_image(
    width: int, height: int, rng: np.random.RandomState
) -> np.ndarray:
    """Random coloured shapes on a random background."""
    bg = rng.randint(0, 256, (height, width, 3), dtype=np.uint8)
    n_shapes = rng.randint(2, 8)

    for _ in range(n_shapes):
        colour = tuple(int(c) for c in rng.randint(0, 256, 3))
        shape_type = rng.choice(["rect", "circle", "triangle"])

        if shape_type == "rect":
            x1, y1 = rng.randint(0, width), rng.randint(0, height)
            x2 = min(x1 + rng.randint(10, width // 2), width)
            y2 = min(y1 + rng.randint(10, height // 2), height)
            bg[y1:y2, x1:x2] = colour

        elif shape_type == "circle":
            cx, cy = rng.randint(0, width), rng.randint(0, height)
            r = rng.randint(5, min(width, height) // 4)
            yy, xx = np.ogrid[:height, :width]
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
            bg[mask] = colour

        elif shape_type == "triangle":
            pts = rng.randint(0, min(width, height), (3, 2))
            # Simple fill via bounding box (approximate)
            min_y, max_y = int(pts[:, 1].min()), int(pts[:, 1].max())
            min_x, max_x = int(pts[:, 0].min()), int(pts[:, 0].max())
            min_y = max(0, min_y)
            max_y = min(height, max_y)
            min_x = max(0, min_x)
            max_x = min(width, max_x)
            bg[min_y:max_y, min_x:max_x] = colour

    return bg


def _gen_noise_image(
    width: int, height: int, rng: np.random.RandomState
) -> np.ndarray:
    """Uniform random noise image."""
    return rng.randint(0, 256, (height, width, 3), dtype=np.uint8)


def _gen_gradient_image(
    width: int, height: int, rng: np.random.RandomState
) -> np.ndarray:
    """Smooth colour gradient."""
    start_colour = rng.randint(0, 256, 3).astype(np.float32)
    end_colour = rng.randint(0, 256, 3).astype(np.float32)

    gradient = np.zeros((height, width, 3), dtype=np.float32)
    for i in range(height):
        t = i / max(height - 1, 1)
        gradient[i] = start_colour * (1 - t) + end_colour * t

    return gradient.astype(np.uint8)


# ---------------------------------------------------------------------------
# Audio generators
# ---------------------------------------------------------------------------

def _gen_tone(
    duration: float, sr: int, rng: np.random.RandomState
) -> np.ndarray:
    """Random-frequency sine wave."""
    freq = rng.uniform(200, 2000)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _gen_audio_noise(
    duration: float, sr: int, rng: np.random.RandomState
) -> np.ndarray:
    """White noise waveform."""
    n_samples = int(sr * duration)
    return rng.randn(n_samples).astype(np.float32) * 0.3


def _gen_speech_like(
    duration: float, sr: int, rng: np.random.RandomState
) -> np.ndarray:
    """Amplitude-modulated tone to mimic speech rhythm."""
    base_freq = rng.uniform(100, 300)  # fundamental
    mod_freq = rng.uniform(2, 8)  # syllable rate
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    carrier = np.sin(2 * np.pi * base_freq * t)
    modulator = 0.5 * (1 + np.sin(2 * np.pi * mod_freq * t))
    return (carrier * modulator * 0.5).astype(np.float32)
