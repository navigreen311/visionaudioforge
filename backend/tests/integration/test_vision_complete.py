"""Comprehensive vision pipeline E2E tests.

Tests verify the FULL flow by importing service classes directly
(not via API) and exercising each pipeline end-to-end.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.vision.preprocessing import ImagePreprocessor
from app.services.vision.motion import MotionAnalyzer
from app.services.vision.visualization import create_motion_heatmap
from app.services.vision.detection import ObjectDetector
from app.services.vision.tracking import CentroidTracker
from app.services.vision.segmentation import SegmentationService
from app.services.vision.error_analysis import (
    compute_confusion_matrix,
    class_level_metrics,
)
from app.services.vision.depth import DepthEstimator
from app.services.vision.anomaly import AnomalyDetector
from app.services.vision.face_plate import FacePlateDetector
from app.services.vision.screen_intel import ScreenIntelligence

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rgb_image(h: int = 120, w: int = 160) -> np.ndarray:
    """Create a synthetic 3-channel RGB test image with varied content."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Gradient across red channel
    img[:, :, 0] = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    # Solid green band in the middle
    img[h // 3 : 2 * h // 3, :, 1] = 180
    # Blue corner
    img[: h // 4, : w // 4, 2] = 200
    return img


def _make_bgr_image(h: int = 120, w: int = 160) -> np.ndarray:
    """Create a synthetic BGR test image (OpenCV convention)."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 0] = 100  # B
    img[:, :, 1] = 150  # G
    img[:, :, 2] = 200  # R
    # Add a bright rectangle for feature detection
    img[30:90, 40:120] = (255, 255, 255)
    return img


def _make_frame_with_rect(
    h: int = 120,
    w: int = 160,
    rect_x: int = 20,
    rect_y: int = 20,
    rect_w: int = 30,
    rect_h: int = 30,
) -> np.ndarray:
    """Create a grayscale frame with a white rectangle at a given position."""
    frame = np.zeros((h, w), dtype=np.uint8)
    x1, y1 = rect_x, rect_y
    x2, y2 = min(rect_x + rect_w, w), min(rect_y + rect_h, h)
    frame[y1:y2, x1:x2] = 255
    return frame


# ---------------------------------------------------------------------------
# 1. Preprocessing full pipeline
# ---------------------------------------------------------------------------

class TestPreprocessingFullPipeline:

    def test_preprocessing_full_pipeline(self):
        """Create test image -> min_max_normalize -> verify [0,1] ->
        z_score -> verify mean~0 -> convert RGB->HSV -> verify 3ch ->
        edge_detect -> verify binary output.
        """
        preprocessor = ImagePreprocessor()
        img = _make_rgb_image()

        # Step 1: min-max normalize
        normed = preprocessor.min_max_normalize(img)
        assert normed.dtype == np.float32
        assert normed.min() >= 0.0 - 1e-6
        assert normed.max() <= 1.0 + 1e-6

        # Step 2: z-score normalize (on original, not on 0-1 image)
        z_scored = preprocessor.z_score_normalize(img)
        assert z_scored.dtype == np.float32
        assert abs(float(z_scored.mean())) < 1e-4, "z-score mean should be ~0"

        # Step 3: color conversion RGB -> HSV
        hsv = preprocessor.convert_color_space(img, "rgb", "hsv")
        assert hsv.ndim == 3
        assert hsv.shape[2] == 3, "HSV image must have 3 channels"

        # Step 4: edge detection on original
        edges = preprocessor.edge_detection(img, method="canny")
        assert edges.ndim == 2, "Edge map should be 2-D (grayscale)"
        unique_vals = set(np.unique(edges))
        assert unique_vals.issubset({0, 255}), "Canny output should be binary (0 or 255)"


# ---------------------------------------------------------------------------
# 2. Optical flow full pipeline
# ---------------------------------------------------------------------------

class TestOpticalFlowFullPipeline:

    def test_optical_flow_full_pipeline(self):
        """Create 2 frames with moving rectangle -> lucas_kanade ->
        verify motion detected -> farneback -> verify dense flow shape ->
        motion_heatmap -> verify 3-channel output.
        """
        analyzer = MotionAnalyzer()

        # Frame 1: rectangle at (20, 20)
        frame1 = _make_frame_with_rect(rect_x=20, rect_y=20)
        # Frame 2: rectangle moved to (50, 20)
        frame2 = _make_frame_with_rect(rect_x=50, rect_y=20)

        # --- Lucas-Kanade sparse flow ---
        lk_result = analyzer.lucas_kanade(frame1, frame2)
        assert isinstance(lk_result, dict)
        assert "mean_magnitude" in lk_result
        assert "num_tracked" in lk_result
        # Motion should be detected (rectangle moved 30px)
        if lk_result["num_tracked"] > 0:
            assert lk_result["mean_magnitude"] > 0, "Expected nonzero motion magnitude"

        # --- Farneback dense flow ---
        fb_result = analyzer.farneback_dense(frame1, frame2)
        assert isinstance(fb_result, dict)
        flow = fb_result["flow"]
        assert flow.shape == (*frame1.shape, 2), "Dense flow must be (H, W, 2)"
        assert fb_result["max_magnitude"] >= 0

        # --- Motion heatmap from dense flow ---
        heatmap = create_motion_heatmap(flow)
        assert heatmap.ndim == 3
        assert heatmap.shape[2] == 3, "Heatmap must be 3-channel (HSV)"
        assert heatmap.shape[:2] == frame1.shape[:2]


# ---------------------------------------------------------------------------
# 3. Detection pipeline
# ---------------------------------------------------------------------------

class TestDetectionPipeline:

    def test_detection_pipeline(self):
        """Create test image -> ObjectDetector.detect -> verify returns list
        (may be empty without real model) -> verify graceful handling.
        """
        detector = ObjectDetector()
        img = _make_bgr_image()

        detections = detector.detect(img)
        assert isinstance(detections, list), "detect() must return a list"
        # Without ultralytics installed the list may be empty -- that is OK.
        # If detections are returned, verify structure.
        for det in detections:
            assert "bbox" in det
            assert "class_id" in det
            assert "class_name" in det
            assert "confidence" in det


# ---------------------------------------------------------------------------
# 4. Tracking pipeline
# ---------------------------------------------------------------------------

class TestTrackingPipeline:

    def test_tracking_pipeline(self):
        """Create 3 frames with moving object -> CentroidTracker ->
        verify consistent ID across frames -> verify trajectory.
        """
        tracker = CentroidTracker(max_disappeared=50, distance_threshold=80.0)

        # Frame 1: object at (50, 50)
        result1 = tracker.update([[50.0, 50.0]])
        assert len(result1) == 1
        first_id = list(result1.keys())[0]

        # Frame 2: object moves to (55, 52)
        result2 = tracker.update([[55.0, 52.0]])
        assert len(result2) == 1
        second_id = list(result2.keys())[0]
        assert first_id == second_id, "Same object should keep its ID"

        # Frame 3: object moves to (60, 54)
        result3 = tracker.update([[60.0, 54.0]])
        assert len(result3) == 1
        third_id = list(result3.keys())[0]
        assert first_id == third_id, "ID must remain consistent across 3 frames"

        # Verify the tracked centroid matches the latest input
        assert result3[third_id] == [60.0, 54.0]


# ---------------------------------------------------------------------------
# 5. Segmentation pipeline
# ---------------------------------------------------------------------------

class TestSegmentationPipeline:

    def test_segmentation_pipeline(self):
        """Create test image -> semantic_segmentation -> verify mask shape
        matches image -> instance_segmentation -> verify list output.
        """
        seg = SegmentationService()
        img = _make_bgr_image()
        h, w = img.shape[:2]

        # Semantic segmentation
        sem_result = seg.semantic_segmentation(img)
        assert "mask" in sem_result
        mask = sem_result["mask"]
        assert mask.shape == (h, w), "Mask shape must match image (H, W)"
        assert "classes" in sem_result

        # Instance segmentation (with synthetic detections)
        fake_detections = [
            {"bbox": [40, 30, 120, 90], "class_name": "object_a"},
            {"bbox": [0, 0, 30, 30], "class_name": "object_b"},
        ]
        instances = seg.instance_segmentation(img, fake_detections)
        assert isinstance(instances, list)
        assert len(instances) == 2
        for inst in instances:
            assert "mask" in inst
            assert "class" in inst
            assert inst["mask"].shape == (h, w)


# ---------------------------------------------------------------------------
# 6. Error analysis pipeline
# ---------------------------------------------------------------------------

class TestErrorAnalysisPipeline:

    def test_error_analysis_pipeline(self):
        """Create known predictions/ground_truth -> compute_confusion_matrix
        -> verify shape -> class_level_metrics -> verify precision/recall/f1.
        """
        classes = ["cat", "dog", "bird"]
        y_true = ["cat", "cat", "dog", "dog", "bird", "bird", "cat", "dog", "bird"]
        y_pred = ["cat", "dog", "dog", "dog", "bird", "cat", "cat", "bird", "bird"]

        cm = compute_confusion_matrix(y_true, y_pred, classes)
        assert cm.shape == (3, 3), "Confusion matrix should be (n_classes, n_classes)"
        assert cm.sum() == len(y_true), "Total counts must equal sample count"

        metrics = class_level_metrics(cm, classes)
        assert len(metrics) == 3
        for m in metrics:
            assert "precision" in m
            assert "recall" in m
            assert "f1" in m
            assert 0.0 <= m["precision"] <= 1.0
            assert 0.0 <= m["recall"] <= 1.0
            assert 0.0 <= m["f1"] <= 1.0

        # Verify a known value: "dog" has TP=2, predicted_total=col-sum for dog
        dog_idx = classes.index("dog")
        dog_tp = cm[dog_idx, dog_idx]
        assert dog_tp == 2, "dog TP should be 2"


# ---------------------------------------------------------------------------
# 7. Depth estimation
# ---------------------------------------------------------------------------

class TestDepthEstimation:

    def test_depth_estimation(self):
        """Create test image -> estimate_depth -> verify depth_map shape
        matches, values 0-1.
        """
        estimator = DepthEstimator()
        img = _make_bgr_image()
        h, w = img.shape[:2]

        result = estimator.estimate_depth(img)
        assert "depth_map" in result
        depth_map = result["depth_map"]
        assert depth_map.shape == (h, w), "Depth map must be (H, W)"
        assert depth_map.dtype == np.float32
        assert float(depth_map.min()) >= 0.0 - 1e-6
        assert float(depth_map.max()) <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# 8. Anomaly detection
# ---------------------------------------------------------------------------

class TestAnomalyDetection:

    def test_anomaly_detection(self):
        """Create normal + abnormal images -> detect_anomaly ->
        verify abnormal is flagged.
        """
        detector = AnomalyDetector()

        # Normal image: moderate brightness, decent contrast
        normal = _make_bgr_image()
        normal_result = detector.detect_anomaly(normal)
        assert isinstance(normal_result, dict)
        assert "is_anomaly" in normal_result
        assert "anomaly_score" in normal_result

        # Abnormal image: almost completely black (very dark)
        abnormal = np.zeros((120, 160, 3), dtype=np.uint8)
        abnormal[:] = 2  # near-black
        abnormal_result = detector.detect_anomaly(abnormal)
        assert abnormal_result["is_anomaly"] is True, (
            "Near-black image should be flagged as anomaly"
        )
        assert abnormal_result["anomaly_score"] > 0.3


# ---------------------------------------------------------------------------
# 9. Face detection
# ---------------------------------------------------------------------------

class TestFaceDetection:

    def test_face_detection(self):
        """Create test image -> detect_faces -> verify returns list structure."""
        detector = FacePlateDetector()
        img = _make_bgr_image()

        faces = detector.detect_faces(img)
        assert isinstance(faces, list), "detect_faces must return a list"
        # A synthetic rectangle image may or may not trigger Haar cascade;
        # either way the structure should be correct.
        for face in faces:
            assert "bbox" in face
            assert "confidence" in face
            assert isinstance(face["bbox"], list)
            assert len(face["bbox"]) == 4


# ---------------------------------------------------------------------------
# 10. Screen intelligence
# ---------------------------------------------------------------------------

class TestScreenIntelligence:

    def test_screen_intelligence(self):
        """Create test image -> analyze_screenshot -> verify returns
        brightness, edge_density.
        """
        si = ScreenIntelligence()
        img = _make_bgr_image()

        result = si.analyze_screenshot(img)
        assert isinstance(result, dict)
        assert "brightness" in result
        assert "edge_density" in result
        assert isinstance(result["brightness"], float)
        assert isinstance(result["edge_density"], float)
        assert 0.0 <= result["brightness"] <= 255.0
        assert 0.0 <= result["edge_density"] <= 1.0
