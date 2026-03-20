"""Vision services: object detection, OCR, and error analysis."""

from app.services.vision.detection import ObjectDetector
from app.services.vision.ocr import OCREngine
from app.services.vision.error_analysis import (
    compute_confusion_matrix,
    class_level_metrics,
    overall_metrics,
    identify_top_confusions,
    generate_quality_report,
)

__all__ = [
    "ObjectDetector",
    "OCREngine",
    "compute_confusion_matrix",
    "class_level_metrics",
    "overall_metrics",
    "identify_top_confusions",
    "generate_quality_report",
]
