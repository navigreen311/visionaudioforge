"""Tests for panoptic segmentation, ReID tracking, trajectory analysis, and embeddings."""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest

from app.services.vision.segmentation import SegmentationService
from app.services.vision.tracking import ReIDTracker, TrajectoryAnalyzer, cross_camera_match
from app.services.vision.embedding_viz import EmbeddingVisualizer


# ------------------------------------------------------------------
# Panoptic Segmentation
# ------------------------------------------------------------------


class TestPanopticSegmentation:
    def test_panoptic_produces_combined_mask(self):
        """panoptic_segmentation should return stuff_mask, thing_masks, and combined_mask."""
        seg = SegmentationService()

        # Create image with distinct foreground regions
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[:, :] = (30, 30, 30)
        image[20:80, 20:80] = (255, 255, 255)
        image[120:180, 120:180] = (200, 200, 0)

        detections = [
            {"bbox": [10, 10, 90, 90], "class_name": "person"},
            {"bbox": [110, 110, 190, 190], "class_name": "car"},
        ]

        result = seg.panoptic_segmentation(image, detections)

        assert "stuff_mask" in result
        assert "thing_masks" in result
        assert "combined_mask" in result
        assert "class_map" in result
        assert result["stuff_mask"].shape == (200, 200)
        assert result["combined_mask"].shape == (200, 200, 3)
        assert len(result["thing_masks"]) == 2
        assert result["class_map"][0] == "background"

    def test_panoptic_no_detections(self):
        """panoptic_segmentation without detections still produces stuff_mask."""
        seg = SegmentationService()
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :] = (128, 128, 128)

        result = seg.panoptic_segmentation(image)

        assert result["stuff_mask"].shape == (100, 100)
        assert len(result["thing_masks"]) == 0
        assert 0 in result["class_map"]

    def test_mask_to_polygon(self):
        """mask_to_polygon should return contour points from a binary mask."""
        seg = SegmentationService()

        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 1

        polygon = seg.mask_to_polygon(mask)

        assert isinstance(polygon, list)
        assert len(polygon) > 0
        # Each point should be [x, y]
        for point in polygon:
            assert len(point) == 2

    def test_mask_to_polygon_empty(self):
        """mask_to_polygon with empty mask should return empty list."""
        seg = SegmentationService()
        mask = np.zeros((50, 50), dtype=np.uint8)
        polygon = seg.mask_to_polygon(mask)
        assert polygon == []

    def test_mask_iou(self):
        """mask_iou should compute correct IoU between overlapping masks."""
        seg = SegmentationService()

        mask_a = np.zeros((100, 100), dtype=np.uint8)
        mask_a[10:60, 10:60] = 1  # 50x50 = 2500 pixels

        mask_b = np.zeros((100, 100), dtype=np.uint8)
        mask_b[30:80, 30:80] = 1  # 50x50 = 2500 pixels

        iou = seg.mask_iou(mask_a, mask_b)

        # Intersection: [30:60, 30:60] = 30x30 = 900
        # Union: 2500 + 2500 - 900 = 4100
        expected_iou = 900.0 / 4100.0
        assert abs(iou - expected_iou) < 1e-6

    def test_mask_iou_identical(self):
        """mask_iou of identical masks should be 1.0."""
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 1
        iou = SegmentationService.mask_iou(mask, mask)
        assert abs(iou - 1.0) < 1e-6

    def test_mask_iou_no_overlap(self):
        """mask_iou of non-overlapping masks should be 0.0."""
        mask_a = np.zeros((100, 100), dtype=np.uint8)
        mask_a[0:20, 0:20] = 1
        mask_b = np.zeros((100, 100), dtype=np.uint8)
        mask_b[80:100, 80:100] = 1
        iou = SegmentationService.mask_iou(mask_a, mask_b)
        assert iou == 0.0


# ------------------------------------------------------------------
# ReID Tracker
# ------------------------------------------------------------------


class TestReIDTracker:
    def test_reid_uses_appearance(self):
        """ReIDTracker should use appearance features for matching."""
        tracker = ReIDTracker(max_disappeared=30, distance_threshold=200.0)

        # Create a simple BGR image with distinct colored regions
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        image[0:100, 0:150] = (255, 0, 0)   # blue region
        image[0:100, 150:300] = (0, 255, 0)  # green region

        det1 = [{"bbox": [10, 10, 140, 90], "class_name": "person", "confidence": 0.9}]
        results = tracker.update_with_image(det1, image)
        assert len(results) == 1
        tid = results[0]["track_id"]

        # Move slightly but same color region
        det2 = [{"bbox": [15, 15, 145, 95], "class_name": "person", "confidence": 0.88}]
        results = tracker.update_with_image(det2, image)
        assert len(results) == 1
        assert results[0]["track_id"] == tid

    def test_histogram_similarity(self):
        """histogram_similarity should return 1.0 for identical histograms."""
        hist = np.random.default_rng(42).random(512).astype(np.float32)
        hist /= hist.sum()
        sim = ReIDTracker.histogram_similarity(hist, hist)
        assert abs(sim - 1.0) < 1e-4

    def test_compute_appearance_feature_shape(self):
        """compute_appearance_feature should return a 512-element histogram."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :] = (100, 150, 200)
        feat = ReIDTracker.compute_appearance_feature(image, [10, 10, 90, 90])
        assert feat.shape == (512,)
        assert abs(feat.sum() - 1.0) < 1e-5  # normalized

    def test_reid_reset_clears_features(self):
        """reset() should clear appearance features."""
        tracker = ReIDTracker()
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        tracker.update_with_image(
            [{"bbox": [0, 0, 50, 50], "class_name": "a", "confidence": 0.9}],
            image,
        )
        assert len(tracker._appearance_features) > 0
        tracker.reset()
        assert len(tracker._appearance_features) == 0


# ------------------------------------------------------------------
# Trajectory Analysis
# ------------------------------------------------------------------


class TestTrajectoryAnalysis:
    def test_trajectory_analysis(self):
        """analyze_trajectory should return expected fields for a rightward path."""
        analyzer = TrajectoryAnalyzer()
        # Straight rightward movement
        history = [[i * 10.0, 50.0] for i in range(20)]
        result = analyzer.analyze_trajectory(history)

        assert "total_distance" in result
        assert "avg_speed" in result
        assert "direction" in result
        assert "is_linear" in result
        assert "curvature" in result
        assert result["direction"] == "right"
        assert result["is_linear"] is True
        assert result["total_distance"] > 0

    def test_trajectory_stationary(self):
        """A stationary trajectory should be detected."""
        analyzer = TrajectoryAnalyzer()
        history = [[50.0, 50.0], [50.0, 50.0], [50.0, 50.0]]
        result = analyzer.analyze_trajectory(history)
        assert result["direction"] == "stationary"
        assert result["total_distance"] == 0.0

    def test_loitering_detection(self):
        """detect_loitering should identify an object staying in a small area."""
        analyzer = TrajectoryAnalyzer()

        # Object moving in small circle for 200 frames
        rng = np.random.default_rng(42)
        history = [[50.0 + rng.uniform(-5, 5), 50.0 + rng.uniform(-5, 5)] for _ in range(200)]

        result = analyzer.detect_loitering(history, threshold_frames=150, radius=50)
        assert result["is_loitering"] is True
        assert result["duration_frames"] == 200
        assert result["area"] > 0

    def test_no_loitering(self):
        """A fast-moving object should not be flagged as loitering."""
        analyzer = TrajectoryAnalyzer()
        history = [[i * 10.0, i * 10.0] for i in range(200)]
        result = analyzer.detect_loitering(history, threshold_frames=150, radius=50)
        assert result["is_loitering"] is False

    def test_position_prediction(self):
        """predict_next_position should extrapolate linearly."""
        analyzer = TrajectoryAnalyzer()
        history = [[0.0, 0.0], [10.0, 5.0], [20.0, 10.0], [30.0, 15.0]]
        predictions = analyzer.predict_next_position(history, steps=3)

        assert len(predictions) == 3
        # Should continue rightward and downward
        for pred in predictions:
            assert len(pred) == 2
        # First prediction should be around [40, 20]
        assert predictions[0][0] > 30.0
        assert predictions[0][1] > 15.0

    def test_position_prediction_single_point(self):
        """With a single point, predictions should repeat that point."""
        analyzer = TrajectoryAnalyzer()
        predictions = analyzer.predict_next_position([[5.0, 10.0]], steps=3)
        assert len(predictions) == 3
        for pred in predictions:
            assert pred == [5.0, 10.0]


# ------------------------------------------------------------------
# Embedding Visualization
# ------------------------------------------------------------------


class TestEmbeddingVisualization:
    def test_embedding_reduction_tsne(self):
        """reduce_dimensions with tsne should produce 2D output."""
        viz = EmbeddingVisualizer()
        rng = np.random.default_rng(42)
        embeddings = rng.random((20, 50)).astype(np.float64)
        reduced = viz.reduce_dimensions(embeddings, method="tsne", n_components=2)
        assert reduced.shape == (20, 2)

    def test_embedding_reduction_pca(self):
        """reduce_dimensions with pca should produce correct shape."""
        viz = EmbeddingVisualizer()
        rng = np.random.default_rng(42)
        embeddings = rng.random((15, 30)).astype(np.float64)
        reduced = viz.reduce_dimensions(embeddings, method="pca", n_components=3)
        assert reduced.shape == (15, 3)

    def test_embedding_clustering(self):
        """cluster_embeddings should return labels, centroids, and silhouette_score."""
        viz = EmbeddingVisualizer()
        rng = np.random.default_rng(42)
        # Create 3 distinct clusters
        cluster1 = rng.random((10, 5)) + np.array([0, 0, 0, 0, 0])
        cluster2 = rng.random((10, 5)) + np.array([10, 10, 10, 10, 10])
        cluster3 = rng.random((10, 5)) + np.array([20, 20, 20, 20, 20])
        embeddings = np.vstack([cluster1, cluster2, cluster3])

        result = viz.cluster_embeddings(embeddings, method="kmeans", n_clusters=3)

        assert "labels" in result
        assert "centroids" in result
        assert "silhouette_score" in result
        assert len(result["labels"]) == 30
        assert result["centroids"].shape == (3, 5)
        assert -1.0 <= result["silhouette_score"] <= 1.0

    def test_plot_returns_base64(self):
        """plot_embeddings should return a valid base64 PNG string."""
        viz = EmbeddingVisualizer()
        rng = np.random.default_rng(42)
        reduced = rng.random((10, 2))
        labels = [0, 0, 0, 1, 1, 1, 2, 2, 2, 2]

        b64_str = viz.plot_embeddings(reduced, labels=labels, title="Test Plot")

        assert isinstance(b64_str, str)
        assert len(b64_str) > 100
        # Verify it's valid base64 by decoding
        decoded = base64.b64decode(b64_str)
        # PNG files start with specific magic bytes
        assert decoded[:4] == b"\x89PNG"

    def test_plot_without_labels(self):
        """plot_embeddings should work without labels."""
        viz = EmbeddingVisualizer()
        reduced = np.random.default_rng(42).random((5, 2))
        b64_str = viz.plot_embeddings(reduced)
        assert isinstance(b64_str, str)
        decoded = base64.b64decode(b64_str)
        assert decoded[:4] == b"\x89PNG"


# ------------------------------------------------------------------
# Cross-camera matching
# ------------------------------------------------------------------


class TestCrossCameraMatch:
    def test_cross_camera_match_identical(self):
        """Identical features across cameras should match."""
        feat = np.random.default_rng(42).random(512).astype(np.float32)
        feat /= feat.sum()
        cam1 = {0: feat}
        cam2 = {5: feat.copy()}
        matches = cross_camera_match(cam1, cam2, threshold=0.7)
        assert len(matches) == 1
        assert matches[0] == (0, 5)

    def test_cross_camera_no_match(self):
        """Very different features should not match."""
        rng = np.random.default_rng(42)
        feat1 = np.zeros(512, dtype=np.float32)
        feat1[0] = 1.0
        feat2 = np.zeros(512, dtype=np.float32)
        feat2[511] = 1.0
        cam1 = {0: feat1}
        cam2 = {1: feat2}
        matches = cross_camera_match(cam1, cam2, threshold=0.7)
        assert len(matches) == 0
