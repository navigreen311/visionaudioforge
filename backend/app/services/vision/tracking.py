"""Multi-object tracking service: SORT-like and centroid-based trackers."""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import TypedDict

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
