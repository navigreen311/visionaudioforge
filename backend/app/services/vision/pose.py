"""Pose estimation service with MediaPipe fallback to stub."""

from __future__ import annotations

import logging
from typing import TypedDict

import cv2
import numpy as np

logger = logging.getLogger(__name__)

KEYPOINT_NAMES: list[str] = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

# Skeleton edges: pairs of keypoint indices to connect
SKELETON_EDGES: list[tuple[int, int]] = [
    (0, 1), (0, 2),       # nose -> eyes
    (1, 3), (2, 4),       # eyes -> ears
    (5, 6),                # shoulders
    (5, 7), (7, 9),       # left arm
    (6, 8), (8, 10),      # right arm
    (5, 11), (6, 12),     # torso
    (11, 12),              # hips
    (11, 13), (13, 15),   # left leg
    (12, 14), (14, 16),   # right leg
]


class Keypoint(TypedDict):
    name: str
    x: float
    y: float
    confidence: float


class Pose(TypedDict):
    keypoints: list[Keypoint]
    bbox: list[float]
    score: float


class PoseEstimator:
    """Pose estimation using MediaPipe when available, stub otherwise.

    Lazily loads MediaPipe on first call. If unavailable, returns an
    empty result with a logged warning.
    """

    def __init__(self) -> None:
        self._mp_pose = None
        self._mp_drawing = None
        self._available: bool | None = None  # None = not yet checked

    def _init_mediapipe(self) -> bool:
        """Attempt to load MediaPipe pose solution."""
        if self._available is not None:
            return self._available

        try:
            import mediapipe as mp  # type: ignore[import-untyped]

            self._mp_pose = mp.solutions.pose
            self._mp_drawing = mp.solutions.drawing_utils
            self._available = True
            logger.info("MediaPipe Pose loaded successfully.")
        except ImportError:
            logger.warning(
                "mediapipe is not installed. Pose estimation is unavailable. "
                "Install with: pip install mediapipe"
            )
            self._available = False

        return self._available

    def estimate(self, image: np.ndarray) -> list[Pose]:
        """Estimate poses in the given image.

        Returns a list of Pose dicts, each with keypoints, bbox, and score.
        If MediaPipe is unavailable, returns an empty list.
        """
        if not self._init_mediapipe():
            logger.warning("Pose estimation skipped — MediaPipe not available.")
            return []

        h, w = image.shape[:2]

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        with self._mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5,
        ) as pose:
            results = pose.process(rgb)

        if not results.pose_landmarks:
            return []

        # MediaPipe returns a single pose per call; wrap in list
        landmarks = results.pose_landmarks.landmark

        # Map MediaPipe's 33 landmarks to our 17-keypoint subset
        # MediaPipe indices: 0=nose, 2=left_eye_inner->1=left_eye(outer=2,we use 2),
        # 5=right_eye(outer=5,we use 5), 7=left_ear, 8=right_ear,
        # 11=left_shoulder, 12=right_shoulder, 13=left_elbow, 14=right_elbow,
        # 15=left_wrist, 16=right_wrist, 23=left_hip, 24=right_hip,
        # 25=left_knee, 26=right_knee, 27=left_ankle, 28=right_ankle
        mp_to_our = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

        keypoints: list[Keypoint] = []
        xs, ys = [], []

        for i, mp_idx in enumerate(mp_to_our):
            lm = landmarks[mp_idx]
            px = lm.x * w
            py = lm.y * h
            keypoints.append(
                Keypoint(
                    name=KEYPOINT_NAMES[i],
                    x=round(px, 2),
                    y=round(py, 2),
                    confidence=round(lm.visibility, 4),
                )
            )
            xs.append(px)
            ys.append(py)

        # Compute bounding box from keypoints
        x1, y1 = min(xs), min(ys)
        x2, y2 = max(xs), max(ys)
        bbox = [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]

        # Overall score: mean visibility
        score = round(float(np.mean([kp["confidence"] for kp in keypoints])), 4)

        return [Pose(keypoints=keypoints, bbox=bbox, score=score)]

    @staticmethod
    def draw_skeleton(
        image: np.ndarray,
        poses: list[Pose],
        keypoint_color: tuple[int, int, int] = (0, 255, 0),
        skeleton_color: tuple[int, int, int] = (255, 0, 0),
        radius: int = 5,
        thickness: int = 2,
    ) -> np.ndarray:
        """Draw keypoints and skeleton edges on the image.

        Returns a copy with annotations.
        """
        canvas = image.copy()

        for pose in poses:
            kps = pose["keypoints"]

            # Draw skeleton edges
            for i, j in SKELETON_EDGES:
                if i < len(kps) and j < len(kps):
                    kp_a = kps[i]
                    kp_b = kps[j]
                    if kp_a["confidence"] > 0.3 and kp_b["confidence"] > 0.3:
                        pt_a = (int(kp_a["x"]), int(kp_a["y"]))
                        pt_b = (int(kp_b["x"]), int(kp_b["y"]))
                        cv2.line(canvas, pt_a, pt_b, skeleton_color, thickness, cv2.LINE_AA)

            # Draw keypoints
            for kp in kps:
                if kp["confidence"] > 0.3:
                    pt = (int(kp["x"]), int(kp["y"]))
                    cv2.circle(canvas, pt, radius, keypoint_color, -1, cv2.LINE_AA)

        return canvas
