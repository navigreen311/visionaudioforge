"""OCR service with pytesseract and graceful fallback."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import numpy as np

logger = logging.getLogger(__name__)


class OCRBlock(TypedDict):
    text: str
    bbox: list[int]
    confidence: float


class OCRResult(TypedDict, total=False):
    full_text: str
    blocks: list[OCRBlock]
    language: str
    error: str


class OCREngine:
    """Tesseract-based OCR with automatic fallback to a stub."""

    def __init__(self) -> None:
        self._available = False
        self._pytesseract: Any | None = None
        try:
            import pytesseract  # type: ignore[import-untyped]

            self._pytesseract = pytesseract
            self._available = True
            logger.info("pytesseract loaded successfully.")
        except ImportError:
            logger.warning(
                "pytesseract is not installed. OCR is unavailable. "
                "Install with: pip install pytesseract"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(self, image: np.ndarray) -> OCRResult:
        """Extract text from an image.

        Returns structured result with full_text, blocks, and language.
        If pytesseract is not installed, returns an error stub.
        """
        if not self._available or self._pytesseract is None:
            return OCRResult(
                full_text="",
                blocks=[],
                language="unknown",
                error="OCR engine not installed",
            )

        pytesseract = self._pytesseract

        # Full text extraction
        full_text: str = pytesseract.image_to_string(image).strip()

        # Block-level data via image_to_data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        blocks: list[OCRBlock] = []
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if text and conf > 0:
                blocks.append(
                    OCRBlock(
                        text=text,
                        bbox=[
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        ],
                        confidence=conf,
                    )
                )

        # Detect language (best-effort)
        try:
            lang_data = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            language = lang_data.get("script", "unknown")
        except Exception:
            language = "unknown"

        return OCRResult(full_text=full_text, blocks=blocks, language=language)
