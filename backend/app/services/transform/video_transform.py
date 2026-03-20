"""Video / Vision Transform Service.

Provides background removal, super-resolution, stabilization, style transfer,
auto-crop, thumbnail generation, and scene detection — all built on OpenCV so
there are zero mandatory heavy-model downloads for V1.
"""

from __future__ import annotations

import math
from typing import Literal

import cv2
import numpy as np


class VideoTransformService:
    """Stateless helper — every public method is a pure image/frame transform."""

    # ------------------------------------------------------------------
    # Background Removal
    # ------------------------------------------------------------------
    def remove_background(
        self,
        image: np.ndarray,
        method: str = "threshold",
    ) -> np.ndarray:
        """Return a 4-channel RGBA image with transparent background.

        Methods
        -------
        threshold  – simple grayscale + Otsu threshold mask (fast, decent on
                     high-contrast subjects).
        grabcut    – OpenCV GrabCut with an auto-initialised rectangle.
        rembg      – high-quality neural-network removal (requires `rembg`
                     package; falls back to threshold if unavailable).
        """
        if method == "rembg":
            try:
                from rembg import remove as rembg_remove  # type: ignore[import-untyped]

                result = rembg_remove(image)
                if result.shape[2] == 4:
                    return result
                return cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
            except ImportError:
                # Fall back to threshold when rembg is not installed.
                method = "threshold"

        if method == "grabcut":
            return self._bg_remove_grabcut(image)

        # Default: threshold
        return self._bg_remove_threshold(image)

    # -- private helpers -------------------------------------------------

    def _bg_remove_threshold(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mask
        return rgba

    def _bg_remove_grabcut(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        margin_x, margin_y = max(1, w // 20), max(1, h // 20)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        mask = np.zeros(image.shape[:2], np.uint8)
        bg_model = np.zeros((1, 65), np.float64)
        fg_model = np.zeros((1, 65), np.float64)

        cv2.grabCut(image, mask, rect, bg_model, fg_model, 5, cv2.GC_INIT_WITH_RECT)

        fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = fg_mask
        return rgba

    # ------------------------------------------------------------------
    # Super Resolution (V1 — high-quality interpolation)
    # ------------------------------------------------------------------
    def super_resolution(self, image: np.ndarray, scale: int = 2) -> np.ndarray:
        """Up-scale an image by *scale* using INTER_CUBIC interpolation.

        For scale == 4 the upscale is applied twice (2x then 2x) to give
        slightly better quality than a single 4x jump.
        """
        if scale <= 1:
            return image.copy()

        if scale == 4:
            intermediate = cv2.resize(
                image,
                None,
                fx=2,
                fy=2,
                interpolation=cv2.INTER_CUBIC,
            )
            return cv2.resize(
                intermediate,
                None,
                fx=2,
                fy=2,
                interpolation=cv2.INTER_CUBIC,
            )

        return cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    # ------------------------------------------------------------------
    # Frame Stabilisation (dense optical-flow)
    # ------------------------------------------------------------------
    def stabilize_frames(self, frames: list[np.ndarray]) -> list[np.ndarray]:
        """Stabilise a sequence of frames using Farneback optical flow.

        For every consecutive pair we estimate a 2-D affine transform (rigid)
        from the dense flow field, then warp each frame to align with the
        first.  A final centre-crop removes the black borders that appear
        after warping.
        """
        if len(frames) < 2:
            return [f.copy() for f in frames]

        h, w = frames[0].shape[:2]
        stabilised: list[np.ndarray] = [frames[0].copy()]
        cumulative = np.eye(2, 3, dtype=np.float64)

        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

        max_dx, max_dy = 0.0, 0.0

        for frame in frames[1:]:
            cur_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, cur_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )

            dx = float(np.median(flow[..., 0]))
            dy = float(np.median(flow[..., 1]))

            transform = np.array([[1, 0, -dx], [0, 1, -dy]], dtype=np.float64)

            cumulative[0, 2] += transform[0, 2]
            cumulative[1, 2] += transform[1, 2]

            max_dx = max(max_dx, abs(cumulative[0, 2]))
            max_dy = max(max_dy, abs(cumulative[1, 2]))

            warped = cv2.warpAffine(frame, cumulative, (w, h))
            stabilised.append(warped)
            prev_gray = cur_gray

        # Centre-crop to remove black borders.
        crop_x = int(math.ceil(max_dx)) + 1
        crop_y = int(math.ceil(max_dy)) + 1
        crop_x = min(crop_x, w // 4)
        crop_y = min(crop_y, h // 4)

        if crop_x > 0 or crop_y > 0:
            stabilised = [
                f[crop_y : h - crop_y, crop_x : w - crop_x] for f in stabilised
            ]

        return stabilised

    # ------------------------------------------------------------------
    # Style Transfer (artistic filters)
    # ------------------------------------------------------------------
    def style_transfer(
        self,
        image: np.ndarray,
        style: str = "sketch",
    ) -> np.ndarray:
        """Apply an artistic style preset to *image*.

        Supported styles: sketch, edges, cartoon, oil_painting.
        """
        dispatch = {
            "sketch": self._style_sketch,
            "edges": self._style_edges,
            "cartoon": self._style_cartoon,
            "oil_painting": self._style_oil_painting,
        }
        fn = dispatch.get(style, self._style_sketch)
        return fn(image)

    def _style_sketch(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        inv = 255 - gray
        blurred = cv2.GaussianBlur(inv, (21, 21), sigmaX=0, sigmaY=0)
        # Dodge-V2 blend: output = min(gray * 256 / (256 - blur), 255)
        sketch = cv2.divide(gray, 255 - blurred, scale=256.0)
        sketch = np.clip(sketch, 0, 255).astype(np.uint8)
        return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    def _style_edges(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        # White edges on black, then invert for a "print" look.
        styled = 255 - edges
        return cv2.cvtColor(styled, cv2.COLOR_GRAY2BGR)

    def _style_cartoon(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
        )
        colour = cv2.bilateralFilter(image, d=9, sigmaColor=300, sigmaSpace=300)
        cartoon = cv2.bitwise_and(colour, colour, mask=edges)
        return cartoon

    def _style_oil_painting(self, image: np.ndarray) -> np.ndarray:
        try:
            return cv2.xphoto.oilPainting(image, 7, 1)  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback: stack of bilateral filters.
            result = image.copy()
            for _ in range(4):
                result = cv2.bilateralFilter(result, d=9, sigmaColor=75, sigmaSpace=75)
            return result

    # ------------------------------------------------------------------
    # Auto Crop
    # ------------------------------------------------------------------
    def auto_crop(
        self,
        image: np.ndarray,
        target_aspect: str = "16:9",
    ) -> np.ndarray:
        """Centre-crop *image* to the given aspect ratio string (e.g. '16:9')."""
        aw, ah = (int(x) for x in target_aspect.split(":"))
        h, w = image.shape[:2]
        target_ratio = aw / ah

        current_ratio = w / h
        if current_ratio > target_ratio:
            # Too wide — crop width.
            new_w = int(h * target_ratio)
            x_start = (w - new_w) // 2
            return image[:, x_start : x_start + new_w]
        else:
            # Too tall — crop height.
            new_h = int(w / target_ratio)
            y_start = (h - new_h) // 2
            return image[y_start : y_start + new_h, :]

    # ------------------------------------------------------------------
    # Thumbnail Generation
    # ------------------------------------------------------------------
    def generate_thumbnail(
        self,
        frames: list[np.ndarray],
        method: str = "middle",
    ) -> tuple[np.ndarray, int]:
        """Pick the best frame from *frames* as a thumbnail.

        Returns (frame, index).
        """
        if not frames:
            raise ValueError("frames list must not be empty")

        if method == "first":
            return frames[0], 0

        if method == "brightest":
            brightness = [float(np.mean(f)) for f in frames]
            idx = int(np.argmax(brightness))
            return frames[idx], idx

        # Default: middle
        idx = len(frames) // 2
        return frames[idx], idx

    # ------------------------------------------------------------------
    # Scene Detection
    # ------------------------------------------------------------------
    def scene_detection(
        self,
        frames: list[np.ndarray],
        threshold: float = 30.0,
    ) -> list[int]:
        """Return indices where a scene cut is detected.

        Uses histogram comparison (correlation) between consecutive frames;
        a low correlation (high difference) flags a cut.
        """
        if len(frames) < 2:
            return []

        cuts: list[int] = []

        def _hist(frame: np.ndarray) -> np.ndarray:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            return hist

        prev_hist = _hist(frames[0])
        for i in range(1, len(frames)):
            cur_hist = _hist(frames[i])
            # Bhattacharyya distance: 0 = identical, 1 = totally different.
            diff = cv2.compareHist(prev_hist, cur_hist, cv2.HISTCMP_BHATTACHARYYA)
            # Scale to 0-100 range to match the threshold semantics.
            diff_score = diff * 100.0
            if diff_score > threshold:
                cuts.append(i)
            prev_hist = cur_hist

        return cuts
