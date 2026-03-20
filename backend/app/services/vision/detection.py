"""Object detection service using YOLOv8 with graceful fallback."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Detection(TypedDict):
    bbox: list[float]
    class_id: int
    class_name: str
    confidence: float


class ObjectDetector:
    """Lazy-loading YOLOv8 object detector.

    If ultralytics is not installed, all methods return empty results
    with a logged warning instead of raising.
    """

    def __init__(self, model_name: str = "yolov8n") -> None:
        self._model_name = model_name
        self._model: Any | None = None
        self._available = True

    def _load_model(self) -> Any | None:
        """Lazily load the YOLO model on first use."""
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]

            self._model = YOLO(f"{self._model_name}.pt")
            logger.info("YOLO model '%s' loaded successfully.", self._model_name)
            return self._model
        except ImportError:
            logger.warning(
                "ultralytics is not installed. Object detection is unavailable. "
                "Install with: pip install ultralytics"
            )
            self._available = False
            return None
        except Exception:
            logger.exception("Failed to load YOLO model '%s'.", self._model_name)
            self._available = False
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        image: np.ndarray,
        confidence: float = 0.5,
        classes: list[int] | None = None,
    ) -> list[Detection]:
        """Run detection on a single image.

        Returns a list of Detection dicts with bbox, class info, and confidence.
        """
        model = self._load_model()
        if model is None:
            logger.warning("Detection skipped — model not available.")
            return []

        results = model(image, conf=confidence, classes=classes, verbose=False)
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].tolist()
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                cls_name = result.names.get(cls_id, str(cls_id))
                detections.append(
                    Detection(
                        bbox=xyxy,
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                    )
                )
        return detections

    def detect_batch(
        self,
        images: list[np.ndarray],
        **kwargs: Any,
    ) -> list[list[Detection]]:
        """Run detection on a batch of images."""
        return [self.detect(img, **kwargs) for img in images]

    def draw_detections(
        self,
        image: np.ndarray,
        detections: list[Detection],
        colors: dict[int, tuple[int, int, int]] | None = None,
    ) -> np.ndarray:
        """Draw bounding boxes and labels on the image.

        Returns a copy with annotations drawn.
        """
        annotated = image.copy()
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            cls_id = det["class_id"]

            if colors and cls_id in colors:
                color = colors[cls_id]
            else:
                # Deterministic colour per class
                rng = np.random.default_rng(cls_id)
                color = tuple(int(c) for c in rng.integers(50, 255, size=3))

            label = f"{det['class_name']} {det['confidence']:.2f}"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return annotated
