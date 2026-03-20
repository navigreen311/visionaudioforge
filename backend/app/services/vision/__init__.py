"""Vision services: detection, OCR, error analysis, tracking, segmentation, pose,
depth estimation, anomaly detection, face/plate detection, screen intelligence."""

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
from app.services.vision.depth import DepthEstimator
from app.services.vision.anomaly import AnomalyDetector
from app.services.vision.face_plate import FacePlateDetector
from app.services.vision.screen_intel import ScreenIntelligence

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
    "DepthEstimator",
    "AnomalyDetector",
    "FacePlateDetector",
    "ScreenIntelligence",
]
