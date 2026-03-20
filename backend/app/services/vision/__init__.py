"""Vision services: detection, OCR, error analysis, tracking, segmentation, pose."""

from app.services.vision.detection import ObjectDetector
from app.services.vision.ocr import OCREngine
from app.services.vision.error_analysis import (
    compute_confusion_matrix,
    class_level_metrics,
    overall_metrics,
    identify_top_confusions,
    generate_quality_report,
)
from app.services.vision.tracking import MultiObjectTracker, CentroidTracker
from app.services.vision.segmentation import SegmentationService
from app.services.vision.pose import PoseEstimator, KEYPOINT_NAMES

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
    "SegmentationService",
    "PoseEstimator",
    "KEYPOINT_NAMES",
]
