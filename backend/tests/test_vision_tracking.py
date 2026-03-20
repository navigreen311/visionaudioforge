"""Tests for multi-object tracking, segmentation, and pose estimation."""

from __future__ import annotations

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.services.vision.tracking import CentroidTracker, MultiObjectTracker
from app.services.vision.segmentation import SegmentationService
from app.services.vision.pose import KEYPOINT_NAMES, PoseEstimator
from tests.utils import create_test_image_with_shapes, image_to_png_bytes


# ------------------------------------------------------------------
# Centroid Tracker
# ------------------------------------------------------------------


class TestCentroidTracker:
    def test_centroid_tracker_assigns_ids(self):
        """3 frames of a moving object should maintain consistent ID."""
        ct = CentroidTracker(max_disappeared=50)

        # Frame 1: one object at (50, 50)
        objects = ct.update([[50.0, 50.0]])
        assert len(objects) == 1
        first_id = list(objects.keys())[0]

        # Frame 2: object moves to (55, 52)
        objects = ct.update([[55.0, 52.0]])
        assert len(objects) == 1
        assert first_id in objects

        # Frame 3: object moves to (60, 55)
        objects = ct.update([[60.0, 55.0]])
        assert len(objects) == 1
        assert first_id in objects

    def test_tracker_handles_new_objects(self):
        """An object appearing mid-sequence should get a new ID."""
        ct = CentroidTracker(max_disappeared=50)

        # Frame 1: one object
        objects = ct.update([[50.0, 50.0]])
        assert len(objects) == 1
        first_id = list(objects.keys())[0]

        # Frame 2: two objects (original + new)
        objects = ct.update([[52.0, 51.0], [200.0, 200.0]])
        assert len(objects) == 2
        assert first_id in objects
        ids = list(objects.keys())
        new_id = [i for i in ids if i != first_id][0]
        assert new_id != first_id

    def test_tracker_removes_disappeared(self):
        """Object gone for max_disappeared+ frames should be removed."""
        ct = CentroidTracker(max_disappeared=5)

        # Register one object
        objects = ct.update([[50.0, 50.0]])
        assert len(objects) == 1

        # Send empty updates for 6 frames (exceeds max_disappeared=5)
        for _ in range(6):
            objects = ct.update([])

        assert len(objects) == 0


# ------------------------------------------------------------------
# Multi-Object Tracker (SORT-like)
# ------------------------------------------------------------------


class TestMultiObjectTracker:
    def test_sort_tracker_assigns_and_maintains_ids(self):
        """Objects tracked across frames should keep same track_id."""
        tracker = MultiObjectTracker(method="sort", max_disappeared=30)

        det1 = [{"bbox": [10, 10, 50, 50], "class_name": "person", "confidence": 0.9}]
        results = tracker.update(det1)
        assert len(results) == 1
        tid = results[0]["track_id"]

        det2 = [{"bbox": [12, 12, 52, 52], "class_name": "person", "confidence": 0.88}]
        results = tracker.update(det2)
        assert len(results) == 1
        assert results[0]["track_id"] == tid
        assert results[0]["age"] == 2

    def test_sort_tracker_new_object_mid_sequence(self):
        """A new detection far from existing tracks gets a new ID."""
        tracker = MultiObjectTracker(method="sort", max_disappeared=30)

        det1 = [{"bbox": [10, 10, 50, 50], "class_name": "car", "confidence": 0.8}]
        tracker.update(det1)

        det2 = [
            {"bbox": [12, 12, 52, 52], "class_name": "car", "confidence": 0.8},
            {"bbox": [300, 300, 400, 400], "class_name": "person", "confidence": 0.7},
        ]
        results = tracker.update(det2)
        assert len(results) == 2
        ids = {r["track_id"] for r in results}
        assert len(ids) == 2

    def test_trajectories(self):
        """get_trajectories returns centroid history per track."""
        tracker = MultiObjectTracker(method="sort")

        tracker.update([{"bbox": [0, 0, 10, 10], "class_name": "a", "confidence": 0.9}])
        tracker.update([{"bbox": [2, 2, 12, 12], "class_name": "a", "confidence": 0.9}])

        trajectories = tracker.get_trajectories()
        assert len(trajectories) == 1
        tid = list(trajectories.keys())[0]
        assert len(trajectories[tid]) == 2

    def test_reset_clears_state(self):
        """reset() should clear all tracks."""
        tracker = MultiObjectTracker(method="sort")
        tracker.update([{"bbox": [0, 0, 10, 10], "class_name": "a", "confidence": 0.9}])
        assert len(tracker.get_trajectories()) == 1
        tracker.reset()
        assert len(tracker.get_trajectories()) == 0


# ------------------------------------------------------------------
# Segmentation
# ------------------------------------------------------------------


class TestSegmentation:
    def test_segmentation_returns_mask(self):
        """Semantic segmentation mask shape must match image H, W."""
        seg = SegmentationService()
        image = create_test_image_with_shapes(200, 200)
        # Convert RGB to BGR for OpenCV
        import cv2

        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        result = seg.semantic_segmentation(image_bgr)

        assert "mask" in result
        assert result["mask"].shape == (200, 200)
        assert "classes" in result
        assert "background" in result["classes"]
        assert "foreground" in result["classes"]

    def test_mask_overlay_preserves_shape(self):
        """mask_overlay output must have same shape as input image."""
        seg = SegmentationService()
        image = np.zeros((100, 150, 3), dtype=np.uint8)
        image[:, :] = (50, 100, 150)

        mask = np.zeros((100, 150), dtype=np.uint8)
        mask[20:80, 30:120] = 1

        overlay = seg.mask_overlay(image, [mask])
        assert overlay.shape == image.shape

    def test_export_masks_returns_base64(self):
        """export_masks should return base64 strings."""
        seg = SegmentationService()
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 1
        encoded = seg.export_masks([mask], format="png")
        assert len(encoded) == 1
        assert isinstance(encoded[0], str)
        assert len(encoded[0]) > 0

    def test_instance_segmentation(self):
        """Instance segmentation should return one result per detection."""
        seg = SegmentationService()
        # Create image with clear foreground regions for reliable GrabCut
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[:, :] = (30, 30, 30)  # dark background
        image[20:80, 20:80] = (255, 255, 255)  # bright region 1
        image[110:170, 110:170] = (200, 200, 0)  # bright region 2
        detections = [
            {"bbox": [10, 10, 90, 90], "class_name": "object_a"},
            {"bbox": [100, 100, 180, 180], "class_name": "object_b"},
        ]
        instances = seg.instance_segmentation(image, detections)
        assert len(instances) == 2
        for inst in instances:
            assert "mask" in inst
            assert inst["mask"].shape == (200, 200)
            assert "area" in inst
            assert isinstance(inst["area"], int)


# ------------------------------------------------------------------
# Pose Estimation
# ------------------------------------------------------------------


class TestPoseEstimation:
    def test_pose_keypoint_names(self):
        """There should be exactly 17 keypoint names."""
        assert len(KEYPOINT_NAMES) == 17
        assert "nose" in KEYPOINT_NAMES
        assert "left_shoulder" in KEYPOINT_NAMES
        assert "right_ankle" in KEYPOINT_NAMES

    def test_draw_skeleton_no_crash(self):
        """draw_skeleton should not crash with empty poses."""
        estimator = PoseEstimator()
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = estimator.draw_skeleton(image, [])
        assert result.shape == image.shape

    def test_draw_skeleton_with_pose(self):
        """draw_skeleton should handle a pose dict without crashing."""
        estimator = PoseEstimator()
        image = np.zeros((200, 200, 3), dtype=np.uint8)

        # Build a synthetic pose
        keypoints = []
        for i, name in enumerate(KEYPOINT_NAMES):
            keypoints.append({
                "name": name,
                "x": 100.0 + i * 2,
                "y": 100.0 + i * 2,
                "confidence": 0.9,
            })

        poses = [{"keypoints": keypoints, "bbox": [80, 80, 140, 140], "score": 0.9}]
        result = estimator.draw_skeleton(image, poses)
        assert result.shape == image.shape


# ------------------------------------------------------------------
# API endpoint tests
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_track_endpoint(test_app):
    """POST /api/vision/track should accept frames and return tracking data."""
    img1 = create_test_image_with_shapes(100, 100)
    img2 = create_test_image_with_shapes(100, 100)
    png1 = image_to_png_bytes(img1)
    png2 = image_to_png_bytes(img2)

    response = await test_app.post(
        "/api/vision/track",
        files=[
            ("files", ("frame1.png", png1, "image/png")),
            ("files", ("frame2.png", png2, "image/png")),
        ],
        params={"method": "sort"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "frames" in data
    assert "trajectories" in data
    assert "total_frames" in data
    assert data["total_frames"] == 2


@pytest.mark.anyio
async def test_api_segment_endpoint(test_app):
    """POST /api/vision/segment should return segmentation results."""
    img = create_test_image_with_shapes(100, 100)
    png = image_to_png_bytes(img)

    response = await test_app.post(
        "/api/vision/segment",
        files={"file": ("test.png", png, "image/png")},
        params={"method": "semantic"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "method" in data
    assert data["method"] == "semantic"
    assert "classes" in data
    assert "overlay" in data
