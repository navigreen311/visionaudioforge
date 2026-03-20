"""Face and license plate detection service."""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FacePlateDetector:
    """Detect faces and license plates using OpenCV Haar cascades.

    Uses cv2.CascadeClassifier with pre-trained Haar cascade XML files
    shipped with OpenCV. OCR on plate regions uses pytesseract if available.
    """

    def __init__(self) -> None:
        self._face_cascade: cv2.CascadeClassifier | None = None
        self._profile_cascade: cv2.CascadeClassifier | None = None
        self._plate_cascade: cv2.CascadeClassifier | None = None
        self._tesseract_available: bool | None = None

    def _get_face_cascade(self) -> cv2.CascadeClassifier:
        if self._face_cascade is None:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(path)
            if self._face_cascade.empty():
                logger.warning("Failed to load frontal face cascade from %s", path)
        return self._face_cascade

    def _get_profile_cascade(self) -> cv2.CascadeClassifier | None:
        if self._profile_cascade is None:
            path = cv2.data.haarcascades + "haarcascade_profileface.xml"
            self._profile_cascade = cv2.CascadeClassifier(path)
            if self._profile_cascade.empty():
                logger.debug("Profile face cascade not available at %s", path)
                self._profile_cascade = None
        return self._profile_cascade

    def _get_plate_cascade(self) -> cv2.CascadeClassifier:
        if self._plate_cascade is None:
            path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
            self._plate_cascade = cv2.CascadeClassifier(path)
            if self._plate_cascade.empty():
                logger.warning("Failed to load plate cascade from %s", path)
        return self._plate_cascade

    def _is_tesseract_available(self) -> bool:
        if self._tesseract_available is None:
            try:
                import pytesseract  # noqa: F401

                self._tesseract_available = True
            except ImportError:
                self._tesseract_available = False
                logger.debug("pytesseract not available — plate OCR disabled")
        return self._tesseract_available

    # ------------------------------------------------------------------
    # Face detection
    # ------------------------------------------------------------------

    def detect_faces(self, image: np.ndarray) -> list[dict]:
        """Detect faces in an image using Haar cascades.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.

        Returns
        -------
        list of dicts with keys: bbox [x, y, w, h], confidence (float).
        """
        if image is None or image.size == 0:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        cascade = self._get_face_cascade()
        faces: list[dict] = []

        if not cascade.empty():
            detections = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            if len(detections) > 0:
                for x, y, w, h in detections:
                    faces.append({
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "confidence": 0.8,  # Haar cascades don't provide confidence
                    })

        # Try profile face detection
        profile_cascade = self._get_profile_cascade()
        if profile_cascade is not None and not profile_cascade.empty():
            profile_detections = profile_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            if len(profile_detections) > 0:
                for x, y, w, h in profile_detections:
                    # Check for overlap with existing detections
                    overlaps = False
                    for face in faces:
                        fx, fy, fw, fh = face["bbox"]
                        if (
                            abs(x - fx) < fw // 2
                            and abs(y - fy) < fh // 2
                        ):
                            overlaps = True
                            break
                    if not overlaps:
                        faces.append({
                            "bbox": [int(x), int(y), int(w), int(h)],
                            "confidence": 0.7,
                        })

        return faces

    # ------------------------------------------------------------------
    # License plate detection
    # ------------------------------------------------------------------

    def detect_license_plates(self, image: np.ndarray) -> list[dict]:
        """Detect license plates in an image.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.

        Returns
        -------
        list of dicts with keys: bbox [x, y, w, h], confidence (float),
            text (str or None).
        """
        if image is None or image.size == 0:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        cascade = self._get_plate_cascade()
        plates: list[dict] = []

        if not cascade.empty():
            detections = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(60, 20)
            )
            if len(detections) > 0:
                for x, y, w, h in detections:
                    text = None
                    if self._is_tesseract_available():
                        try:
                            import pytesseract

                            plate_roi = gray[y : y + h, x : x + w]
                            # Preprocess for OCR
                            plate_roi = cv2.resize(plate_roi, (200, 50))
                            _, plate_roi = cv2.threshold(
                                plate_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                            )
                            raw_text = pytesseract.image_to_string(
                                plate_roi,
                                config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                            )
                            text = raw_text.strip() or None
                        except Exception:
                            logger.debug("Plate OCR failed for region (%d,%d,%d,%d)", x, y, w, h)

                    plates.append({
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "confidence": 0.7,
                        "text": text,
                    })

        return plates

    # ------------------------------------------------------------------
    # Blur and drawing utilities
    # ------------------------------------------------------------------

    def blur_regions(
        self,
        image: np.ndarray,
        regions: list[list[int]],
        method: str = "gaussian",
        kernel: int = 99,
    ) -> np.ndarray:
        """Apply blur to specified bounding box regions.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.
        regions : list of [x, y, w, h]
            Bounding boxes to blur.
        method : str
            Blur method: 'gaussian' or 'pixelate'.
        kernel : int
            Kernel size for Gaussian blur (must be odd).

        Returns
        -------
        np.ndarray with blurred regions.
        """
        result = image.copy()
        h_img, w_img = result.shape[:2]

        # Ensure kernel is odd
        if kernel % 2 == 0:
            kernel += 1

        for region in regions:
            x, y, w, h = region
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(w_img, x + w)
            y2 = min(h_img, y + h)

            if x2 <= x1 or y2 <= y1:
                continue

            roi = result[y1:y2, x1:x2]

            if method == "pixelate":
                small = cv2.resize(roi, (max(1, w // 10), max(1, h // 10)))
                blurred = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
            else:
                blurred = cv2.GaussianBlur(roi, (kernel, kernel), 0)

            result[y1:y2, x1:x2] = blurred

        return result

    def draw_detections(
        self,
        image: np.ndarray,
        faces: list[dict] | None = None,
        plates: list[dict] | None = None,
    ) -> np.ndarray:
        """Draw labeled bounding boxes for faces and plates.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.
        faces : list of detection dicts or None
        plates : list of detection dicts or None

        Returns
        -------
        np.ndarray with annotations drawn.
        """
        annotated = image.copy()

        if faces:
            for det in faces:
                x, y, w, h = det["bbox"]
                conf = det.get("confidence", 0.0)
                label = f"Face {conf:.2f}"
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    annotated, label, (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
                )

        if plates:
            for det in plates:
                x, y, w, h = det["bbox"]
                conf = det.get("confidence", 0.0)
                text = det.get("text") or "?"
                label = f"Plate: {text} ({conf:.2f})"
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(
                    annotated, label, (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA,
                )

        return annotated
