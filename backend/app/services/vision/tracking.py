"""Multi-object tracking service: SORT-like, centroid-based, and ReID trackers."""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import TypedDict

import cv2
import numpy as np


class TrackedObject(TypedDict):
    track_id: int
    bbox: list[float]
    class_name: str
    confidence: float
    age: int
    centroid: list[float]


def _compute_iou(box_a: list[float], box_b: list[float]) -> float:
    """Compute IoU between two [x1, y1, x2, y2] boxes."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter == 0:
        return 0.0

    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / (area_a + area_b - inter)


def _bbox_centroid(bbox: list[float]) -> list[float]:
    """Compute centroid [cx, cy] from [x1, y1, x2, y2]."""
    return [(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0]


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


class MultiObjectTracker:
    """SORT-like multi-object tracker using centroid-distance matching.

    For each frame, match new detections to existing tracks by finding
    the nearest existing track centroid. If distance < threshold, update
    the track; otherwise create a new track. Tracks not updated for
    ``max_disappeared`` frames are removed.
    """

    def __init__(self, method: str = "sort", max_disappeared: int = 30, distance_threshold: float = 100.0) -> None:
        self.method = method
        self.max_disappeared = max_disappeared
        self.distance_threshold = distance_threshold

        self._next_id = 0
        # track_id -> latest TrackedObject
        self._tracks: dict[int, TrackedObject] = {}
        # track_id -> frames since last update
        self._disappeared: dict[int, int] = {}
        # track_id -> list of centroids (trajectory)
        self._trajectories: dict[int, list[list[float]]] = {}

    def update(self, detections: list[dict]) -> list[TrackedObject]:
        """Match detections to existing tracks and return updated list.

        Each detection dict must contain at least: bbox, class_name, confidence.
        """
        if len(detections) == 0:
            # Mark all existing tracks as disappeared
            to_remove = []
            for tid in list(self._disappeared):
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self.max_disappeared:
                    to_remove.append(tid)
            for tid in to_remove:
                self._deregister(tid)
            return list(self._tracks.values())

        det_centroids = [_bbox_centroid(d["bbox"]) for d in detections]

        if len(self._tracks) == 0:
            # Register all detections as new tracks
            for det, centroid in zip(detections, det_centroids):
                self._register(det, centroid)
            return list(self._tracks.values())

        # Greedy matching: for each detection, find nearest track by centroid distance
        track_ids = list(self._tracks.keys())
        track_centroids = [self._tracks[tid]["centroid"] for tid in track_ids]

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        # Build distance matrix
        distances: list[tuple[float, int, int]] = []
        for di, dc in enumerate(det_centroids):
            for ti_idx, tc in enumerate(track_centroids):
                d = _euclidean(dc, tc)
                distances.append((d, di, ti_idx))

        distances.sort(key=lambda x: x[0])

        for dist, di, ti_idx in distances:
            if di in matched_dets or ti_idx in matched_tracks:
                continue
            if dist > self.distance_threshold:
                continue
            tid = track_ids[ti_idx]
            det = detections[di]
            centroid = det_centroids[di]
            self._tracks[tid] = TrackedObject(
                track_id=tid,
                bbox=det["bbox"],
                class_name=det.get("class_name", ""),
                confidence=det.get("confidence", 0.0),
                age=self._tracks[tid]["age"] + 1,
                centroid=centroid,
            )
            self._trajectories[tid].append(centroid)
            self._disappeared[tid] = 0
            matched_tracks.add(ti_idx)
            matched_dets.add(di)

        # Handle unmatched tracks (disappeared)
        for ti_idx in range(len(track_ids)):
            if ti_idx not in matched_tracks:
                tid = track_ids[ti_idx]
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self.max_disappeared:
                    self._deregister(tid)

        # Handle unmatched detections (new tracks)
        for di in range(len(detections)):
            if di not in matched_dets:
                self._register(detections[di], det_centroids[di])

        return list(self._tracks.values())

    def get_trajectories(self) -> dict[int, list[list[float]]]:
        """Return path history for each active track."""
        return dict(self._trajectories)

    def reset(self) -> None:
        """Clear all tracks and state."""
        self._next_id = 0
        self._tracks.clear()
        self._disappeared.clear()
        self._trajectories.clear()

    def _register(self, detection: dict, centroid: list[float]) -> int:
        tid = self._next_id
        self._next_id += 1
        self._tracks[tid] = TrackedObject(
            track_id=tid,
            bbox=detection["bbox"],
            class_name=detection.get("class_name", ""),
            confidence=detection.get("confidence", 0.0),
            age=1,
            centroid=centroid,
        )
        self._disappeared[tid] = 0
        self._trajectories[tid] = [centroid]
        return tid

    def _deregister(self, track_id: int) -> None:
        del self._tracks[track_id]
        del self._disappeared[track_id]
        del self._trajectories[track_id]


class CentroidTracker:
    """Simple centroid-distance based tracker.

    Maintains a dict of {id: centroid}. On each update, computes pairwise
    distances and uses greedy assignment. New detections get new IDs.
    Missing detections increment a disappeared count. Tracks are removed
    after ``max_disappeared`` frames without updates.
    """

    def __init__(self, max_disappeared: int = 50, distance_threshold: float = 80.0) -> None:
        self.max_disappeared = max_disappeared
        self.distance_threshold = distance_threshold
        self._next_id = 0
        self._objects: OrderedDict[int, list[float]] = OrderedDict()
        self._disappeared: OrderedDict[int, int] = OrderedDict()

    def register(self, centroid: list[float]) -> int:
        """Register a new object with the given centroid."""
        oid = self._next_id
        self._objects[oid] = centroid
        self._disappeared[oid] = 0
        self._next_id += 1
        return oid

    def deregister(self, object_id: int) -> None:
        """Remove a tracked object."""
        del self._objects[object_id]
        del self._disappeared[object_id]

    def update(self, centroids: list[list[float]]) -> OrderedDict[int, list[float]]:
        """Update tracker with new centroid observations.

        Returns OrderedDict mapping object IDs to their current centroids.
        """
        if len(centroids) == 0:
            for oid in list(self._disappeared.keys()):
                self._disappeared[oid] += 1
                if self._disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)
            return self._objects

        if len(self._objects) == 0:
            for c in centroids:
                self.register(c)
            return self._objects

        object_ids = list(self._objects.keys())
        object_centroids = list(self._objects.values())

        # Compute pairwise distances
        dist_matrix = np.zeros((len(object_centroids), len(centroids)))
        for i, oc in enumerate(object_centroids):
            for j, nc in enumerate(centroids):
                dist_matrix[i, j] = _euclidean(oc, nc)

        # Greedy assignment: sort all distances, assign smallest first
        matched_rows: set[int] = set()
        matched_cols: set[int] = set()

        flat_indices = np.argsort(dist_matrix.ravel())
        n_cols = len(centroids)

        for flat_idx in flat_indices:
            row = int(flat_idx // n_cols)
            col = int(flat_idx % n_cols)
            if row in matched_rows or col in matched_cols:
                continue
            if dist_matrix[row, col] > self.distance_threshold:
                continue
            oid = object_ids[row]
            self._objects[oid] = centroids[col]
            self._disappeared[oid] = 0
            matched_rows.add(row)
            matched_cols.add(col)

        # Unmatched existing objects: increment disappeared
        for row in range(len(object_ids)):
            if row not in matched_rows:
                oid = object_ids[row]
                self._disappeared[oid] += 1
                if self._disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)

        # Unmatched new centroids: register
        for col in range(len(centroids)):
            if col not in matched_cols:
                self.register(centroids[col])

        return self._objects


class ReIDTracker(MultiObjectTracker):
    """Multi-object tracker with re-identification using appearance features.

    Extends MultiObjectTracker by incorporating color histogram similarity
    alongside centroid distance for track-to-detection matching.
    """

    def __init__(
        self,
        max_disappeared: int = 30,
        distance_threshold: float = 100.0,
        centroid_weight: float = 0.6,
        appearance_weight: float = 0.4,
    ) -> None:
        super().__init__(method="sort", max_disappeared=max_disappeared, distance_threshold=distance_threshold)
        self.centroid_weight = centroid_weight
        self.appearance_weight = appearance_weight
        # track_id -> latest appearance feature (HSV histogram)
        self._appearance_features: dict[int, np.ndarray] = {}

    @staticmethod
    def compute_appearance_feature(image: np.ndarray, bbox: list[float]) -> np.ndarray:
        """Compute HSV color histogram for a bounding box region.

        Args:
            image: Input image (BGR).
            bbox: Bounding box [x1, y1, x2, y2].

        Returns:
            Normalized HSV color histogram (8x8x8 bins), flattened.
        """
        h, w = image.shape[:2]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))

        if x2 - x1 < 1 or y2 - y1 < 1:
            return np.zeros(512, dtype=np.float32)

        roi = image[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256],
        )
        hist = hist.flatten().astype(np.float32)
        norm = np.sum(hist)
        if norm > 0:
            hist /= norm
        return hist

    @staticmethod
    def histogram_similarity(hist_a: np.ndarray, hist_b: np.ndarray) -> float:
        """Compute similarity between two histograms using correlation.

        Returns:
            Correlation coefficient in [-1, 1]. Higher = more similar.
        """
        return float(cv2.compareHist(
            hist_a.astype(np.float32),
            hist_b.astype(np.float32),
            cv2.HISTCMP_CORREL,
        ))

    def match_score(
        self,
        det_centroid: list[float],
        det_feature: np.ndarray,
        track_id: int,
    ) -> float:
        """Compute combined match score for a detection and track.

        Score combines centroid proximity (normalized) and histogram similarity.
        Higher score = better match.
        """
        track_centroid = self._tracks[track_id]["centroid"]
        dist = _euclidean(det_centroid, track_centroid)
        # Convert distance to similarity (0-1 range, inverse of distance)
        centroid_sim = max(0.0, 1.0 - dist / self.distance_threshold)

        track_feat = self._appearance_features.get(track_id)
        if track_feat is not None:
            hist_sim = self.histogram_similarity(det_feature, track_feat)
            # Normalize correlation from [-1,1] to [0,1]
            hist_sim = (hist_sim + 1.0) / 2.0
        else:
            hist_sim = 0.5  # neutral if no appearance on record

        return self.centroid_weight * centroid_sim + self.appearance_weight * hist_sim

    def update_with_image(
        self, detections: list[dict], image: np.ndarray,
    ) -> list[TrackedObject]:
        """Match detections using both centroid distance and appearance.

        Args:
            detections: List of dicts with bbox, class_name, confidence.
            image: Current frame (BGR) for computing appearance features.

        Returns:
            List of updated TrackedObject entries.
        """
        if len(detections) == 0:
            to_remove = []
            for tid in list(self._disappeared):
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self.max_disappeared:
                    to_remove.append(tid)
            for tid in to_remove:
                self._deregister(tid)
            return list(self._tracks.values())

        det_centroids = [_bbox_centroid(d["bbox"]) for d in detections]
        det_features = [
            self.compute_appearance_feature(image, d["bbox"]) for d in detections
        ]

        if len(self._tracks) == 0:
            for det, centroid, feat in zip(detections, det_centroids, det_features):
                tid = self._register(det, centroid)
                self._appearance_features[tid] = feat
            return list(self._tracks.values())

        # Build score matrix (higher = better match)
        track_ids = list(self._tracks.keys())
        scores: list[tuple[float, int, int]] = []
        for di in range(len(detections)):
            for ti_idx, tid in enumerate(track_ids):
                score = self.match_score(det_centroids[di], det_features[di], tid)
                scores.append((score, di, ti_idx))

        # Sort by score descending (best matches first)
        scores.sort(key=lambda x: x[0], reverse=True)

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        for score, di, ti_idx in scores:
            if di in matched_dets or ti_idx in matched_tracks:
                continue
            # Check centroid distance threshold
            tid = track_ids[ti_idx]
            dist = _euclidean(det_centroids[di], self._tracks[tid]["centroid"])
            if dist > self.distance_threshold:
                continue

            det = detections[di]
            centroid = det_centroids[di]
            self._tracks[tid] = TrackedObject(
                track_id=tid,
                bbox=det["bbox"],
                class_name=det.get("class_name", ""),
                confidence=det.get("confidence", 0.0),
                age=self._tracks[tid]["age"] + 1,
                centroid=centroid,
            )
            self._trajectories[tid].append(centroid)
            self._appearance_features[tid] = det_features[di]
            self._disappeared[tid] = 0
            matched_tracks.add(ti_idx)
            matched_dets.add(di)

        # Handle unmatched tracks
        for ti_idx in range(len(track_ids)):
            if ti_idx not in matched_tracks:
                tid = track_ids[ti_idx]
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self.max_disappeared:
                    self._deregister(tid)

        # Handle unmatched detections
        for di in range(len(detections)):
            if di not in matched_dets:
                tid = self._register(detections[di], det_centroids[di])
                self._appearance_features[tid] = det_features[di]

        return list(self._tracks.values())

    def _deregister(self, track_id: int) -> None:
        self._appearance_features.pop(track_id, None)
        super()._deregister(track_id)

    def reset(self) -> None:
        self._appearance_features.clear()
        super().reset()


class TrajectoryAnalyzer:
    """Analyze object trajectories for behavior patterns."""

    @staticmethod
    def analyze_trajectory(track_history: list[list[float]]) -> dict:
        """Analyze a trajectory of centroid positions.

        Args:
            track_history: List of [x, y] centroid positions over time.

        Returns:
            dict with total_distance, avg_speed, direction, is_linear, curvature.
        """
        if len(track_history) < 2:
            return {
                "total_distance": 0.0,
                "avg_speed": 0.0,
                "direction": "stationary",
                "is_linear": True,
                "curvature": 0.0,
            }

        points = np.array(track_history, dtype=np.float64)

        # Total distance
        diffs = np.diff(points, axis=0)
        segment_lengths = np.sqrt(np.sum(diffs ** 2, axis=1))
        total_distance = float(np.sum(segment_lengths))

        # Average speed (distance per frame)
        avg_speed = total_distance / len(segment_lengths)

        # Overall direction based on displacement from first to last
        displacement = points[-1] - points[0]
        dx, dy = displacement[0], displacement[1]

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            direction = "stationary"
        elif abs(dx) >= abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"

        # Linearity: compare total distance to straight-line distance
        straight_dist = float(np.sqrt(dx ** 2 + dy ** 2))
        if total_distance > 1e-6:
            linearity_ratio = straight_dist / total_distance
        else:
            linearity_ratio = 1.0
        is_linear = linearity_ratio > 0.9

        # Curvature: average angular change between consecutive segments
        if len(diffs) < 2:
            curvature = 0.0
        else:
            angles = np.arctan2(diffs[:, 1], diffs[:, 0])
            angle_diffs = np.abs(np.diff(angles))
            # Wrap to [0, pi]
            angle_diffs = np.minimum(angle_diffs, 2 * np.pi - angle_diffs)
            curvature = float(np.mean(angle_diffs))

        return {
            "total_distance": round(total_distance, 4),
            "avg_speed": round(avg_speed, 4),
            "direction": direction,
            "is_linear": is_linear,
            "curvature": round(curvature, 4),
        }

    @staticmethod
    def detect_loitering(
        track_history: list[list[float]],
        threshold_frames: int = 150,
        radius: float = 50.0,
    ) -> dict:
        """Detect if an object is loitering (staying in a small area).

        Args:
            track_history: List of [x, y] centroid positions.
            threshold_frames: Minimum frames to count as loitering.
            radius: Maximum spread radius to count as loitering.

        Returns:
            dict with is_loitering, duration_frames, and area.
        """
        if len(track_history) < 2:
            return {"is_loitering": False, "duration_frames": 0, "area": 0.0}

        points = np.array(track_history, dtype=np.float64)
        centroid = np.mean(points, axis=0)

        # Compute distances from mean centroid
        distances = np.sqrt(np.sum((points - centroid) ** 2, axis=1))
        max_dist = float(np.max(distances))

        # Area of the bounding circle
        area = float(np.pi * max_dist ** 2)

        duration = len(track_history)
        is_loitering = duration >= threshold_frames and max_dist <= radius

        return {
            "is_loitering": is_loitering,
            "duration_frames": duration,
            "area": round(area, 4),
        }

    @staticmethod
    def predict_next_position(
        track_history: list[list[float]], steps: int = 5,
    ) -> list[list[float]]:
        """Predict future positions using linear extrapolation.

        Uses the average velocity from the last N points (up to 10) to
        extrapolate forward.

        Args:
            track_history: List of [x, y] centroid positions.
            steps: Number of future positions to predict.

        Returns:
            List of predicted [x, y] centroid positions.
        """
        if len(track_history) < 2:
            if len(track_history) == 1:
                return [track_history[0][:] for _ in range(steps)]
            return []

        points = np.array(track_history, dtype=np.float64)
        # Use last 10 points max for velocity estimation
        recent = points[-min(10, len(points)):]
        diffs = np.diff(recent, axis=0)
        avg_velocity = np.mean(diffs, axis=0)

        predictions = []
        last_pos = points[-1].copy()
        for i in range(1, steps + 1):
            predicted = last_pos + avg_velocity * i
            predictions.append([round(float(predicted[0]), 4), round(float(predicted[1]), 4)])

        return predictions


def cross_camera_match(
    track_features_cam1: dict[int, np.ndarray],
    track_features_cam2: dict[int, np.ndarray],
    threshold: float = 0.7,
) -> list[tuple[int, int]]:
    """Match tracks across two cameras using appearance feature similarity.

    Args:
        track_features_cam1: dict mapping track_id -> feature vector (camera 1).
        track_features_cam2: dict mapping track_id -> feature vector (camera 2).
        threshold: Minimum similarity score (correlation) for a match.

    Returns:
        List of (cam1_track_id, cam2_track_id) matched pairs.
    """
    matches: list[tuple[int, int]] = []

    ids1 = list(track_features_cam1.keys())
    ids2 = list(track_features_cam2.keys())

    if not ids1 or not ids2:
        return matches

    # Build similarity matrix
    sim_matrix = np.zeros((len(ids1), len(ids2)), dtype=np.float64)
    for i, id1 in enumerate(ids1):
        for j, id2 in enumerate(ids2):
            feat1 = track_features_cam1[id1].astype(np.float32)
            feat2 = track_features_cam2[id2].astype(np.float32)
            sim_matrix[i, j] = cv2.compareHist(feat1, feat2, cv2.HISTCMP_CORREL)

    # Greedy matching by highest similarity first
    matched_rows: set[int] = set()
    matched_cols: set[int] = set()

    flat_indices = np.argsort(sim_matrix.ravel())[::-1]
    n_cols = len(ids2)

    for flat_idx in flat_indices:
        row = int(flat_idx // n_cols)
        col = int(flat_idx % n_cols)
        if row in matched_rows or col in matched_cols:
            continue
        if sim_matrix[row, col] < threshold:
            break  # sorted descending, all remaining are below threshold
        matches.append((ids1[row], ids2[col]))
        matched_rows.add(row)
        matched_cols.add(col)

    return matches
