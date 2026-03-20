"""Vision services: detection, OCR, error analysis, tracking, segmentation, pose, embeddings."""

from app.services.vision.detection import ObjectDetector
from app.services.vision.ocr import OCREngine
from app.services.vision.error_analysis import (
    compute_confusion_matrix,
    class_level_metrics,
    overall_metrics,
    identify_top_confusions,
    generate_quality_report,
)
from app.services.vision.tracking import (
    MultiObjectTracker,
    CentroidTracker,
    ReIDTracker,
    TrajectoryAnalyzer,
    cross_camera_match,
)
from app.services.vision.segmentation import SegmentationService
from app.services.vision.pose import PoseEstimator, KEYPOINT_NAMES
from app.services.vision.embedding_viz import EmbeddingVisualizer

__all__ = [
    "ObjectDetector",
    "OCREngine",
    "compute_confusion_matrix",
    "class_level_metrics",
    "overall_metrics",
    "identify_top_confusions",
    "generate_quality_report",
    "MultiObjectTracker",
    "CentroidTracker",
    "ReIDTracker",
    "TrajectoryAnalyzer",
    "cross_camera_match",
    "SegmentationService",
    "PoseEstimator",
    "KEYPOINT_NAMES",
    "EmbeddingVisualizer",
]
