"""Advanced Video Transform Service — inpainting, frame interpolation, smart crop,
color grading, subtitle burn, and highlight clip selection."""

from __future__ import annotations

import cv2
import numpy as np


class AdvancedVideoTransform:
    """Advanced video/image transforms built on OpenCV."""

    # ------------------------------------------------------------------
    # Inpainting
    # ------------------------------------------------------------------
    async def inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """Inpaint regions indicated by *mask* using Telea method.

        Parameters
        ----------
        image : BGR image (H, W, 3)
        mask  : binary image (H, W) where white (255) pixels = areas to inpaint
        """
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        # Ensure binary
        _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        return cv2.inpaint(image, mask_bin, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

    # ------------------------------------------------------------------
    # Frame Interpolation (Optical Flow)
    # ------------------------------------------------------------------
    async def frame_interpolation(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray,
        num_intermediate: int = 1,
    ) -> list[np.ndarray]:
        """Generate intermediate frames using Farneback optical flow warping.

        Computes dense flow from frame1 to frame2. For each intermediate
        position t in (0, 1), warp frame1 by flow * t.
        """
        if num_intermediate < 1:
            return []

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )

        h, w = frame1.shape[:2]
        intermediates: list[np.ndarray] = []

        for i in range(1, num_intermediate + 1):
            t = i / (num_intermediate + 1)
            # Create remap coordinates
            flow_t = flow * t
            map_x = np.arange(w, dtype=np.float32)[np.newaxis, :] + flow_t[..., 0].astype(np.float32)
            map_y = np.arange(h, dtype=np.float32)[:, np.newaxis] + flow_t[..., 1].astype(np.float32)

            warped = cv2.remap(
                frame1, map_x, map_y,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT,
            )
            intermediates.append(warped)

        return intermediates

    # ------------------------------------------------------------------
    # Smart Crop
    # ------------------------------------------------------------------
    async def smart_crop(
        self,
        image: np.ndarray,
        target_size: tuple[int, int],
        method: str = "center_of_mass",
    ) -> np.ndarray:
        """Intelligently crop *image* to *target_size* (width, height).

        Methods
        -------
        center_of_mass : find center of brightness/edges, crop around it
        face           : detect face with Haar cascade, crop around face
        rule_of_thirds : find interesting region via edge density, align to thirds
        """
        tw, th = target_size
        h, w = image.shape[:2]

        # If image is smaller than target, just resize
        if w <= tw and h <= th:
            return cv2.resize(image, (tw, th))

        if method == "face":
            return self._smart_crop_face(image, tw, th)
        elif method == "rule_of_thirds":
            return self._smart_crop_thirds(image, tw, th)
        else:
            return self._smart_crop_com(image, tw, th)

    def _smart_crop_com(self, image: np.ndarray, tw: int, th: int) -> np.ndarray:
        """Crop around center of mass of edge map."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find center of mass of edges
        moments = cv2.moments(edges)
        if moments["m00"] > 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = w // 2, h // 2

        # Compute crop region centered on (cx, cy)
        x1 = max(0, min(cx - tw // 2, w - tw))
        y1 = max(0, min(cy - th // 2, h - th))
        return image[y1: y1 + th, x1: x1 + tw]

    def _smart_crop_face(self, image: np.ndarray, tw: int, th: int) -> np.ndarray:
        """Crop around detected face."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Try Haar cascade face detection
        try:
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore[attr-defined]
            )
            faces = cascade.detectMultiScale(gray, 1.3, 5)
        except Exception:
            faces = []

        if len(faces) > 0:
            # Use the largest face
            faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            fx, fy, fw, fh = faces_sorted[0]
            cx = fx + fw // 2
            cy = fy + fh // 2
        else:
            # Fallback to center
            cx, cy = w // 2, h // 2

        x1 = max(0, min(cx - tw // 2, w - tw))
        y1 = max(0, min(cy - th // 2, h - th))
        return image[y1: y1 + th, x1: x1 + tw]

    def _smart_crop_thirds(self, image: np.ndarray, tw: int, th: int) -> np.ndarray:
        """Crop to rule of thirds: find region with highest edge density."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Slide a tw x th window and find region with most edge density
        best_score = -1
        best_x, best_y = 0, 0
        step_x = max(1, (w - tw) // 10)
        step_y = max(1, (h - th) // 10)

        for y in range(0, max(1, h - th + 1), step_y):
            for x in range(0, max(1, w - tw + 1), step_x):
                roi = edges[y: y + th, x: x + tw]
                score = float(np.sum(roi))
                if score > best_score:
                    best_score = score
                    best_x, best_y = x, y

        return image[best_y: best_y + th, best_x: best_x + tw]

    # ------------------------------------------------------------------
    # Color Grading
    # ------------------------------------------------------------------
    async def color_grade(
        self,
        image: np.ndarray,
        preset: str = "cinematic",
    ) -> np.ndarray:
        """Apply color grading presets.

        Presets: cinematic, vintage, high_contrast, bw_dramatic.
        """
        dispatch = {
            "cinematic": self._grade_cinematic,
            "vintage": self._grade_vintage,
            "high_contrast": self._grade_high_contrast,
            "bw_dramatic": self._grade_bw_dramatic,
        }
        fn = dispatch.get(preset)
        if fn is None:
            raise ValueError(f"Unknown color grade preset: {preset}")
        return fn(image)

    def _grade_cinematic(self, image: np.ndarray) -> np.ndarray:
        """Slightly desaturate, orange highlights, teal shadows via LAB."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float64)
        L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]

        # Slightly desaturate by pulling A and B toward 128
        A = 128 + (A - 128) * 0.85
        B = 128 + (B - 128) * 0.85

        # Highlights (L > 150): push toward orange (increase A slightly, increase B)
        highlight_mask = L > 150
        A[highlight_mask] += 3
        B[highlight_mask] += 8

        # Shadows (L < 80): push toward teal (decrease A, decrease B slightly)
        shadow_mask = L < 80
        A[shadow_mask] -= 5
        B[shadow_mask] -= 3

        lab[..., 0] = np.clip(L, 0, 255)
        lab[..., 1] = np.clip(A, 0, 255)
        lab[..., 2] = np.clip(B, 0, 255)

        return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)

    def _grade_vintage(self, image: np.ndarray) -> np.ndarray:
        """Reduce contrast, add sepia tone, slight vignette."""
        result = image.astype(np.float64)

        # Reduce contrast
        result = 0.7 * result + 0.3 * 128.0

        # Sepia tone
        sepia_kernel = np.array([
            [0.272, 0.534, 0.131],
            [0.349, 0.686, 0.168],
            [0.393, 0.769, 0.189],
        ])
        # Apply sepia (BGR input, sepia expects RGB-like)
        b, g, r = result[..., 0], result[..., 1], result[..., 2]
        new_r = r * sepia_kernel[0, 0] + g * sepia_kernel[0, 1] + b * sepia_kernel[0, 2]
        new_g = r * sepia_kernel[1, 0] + g * sepia_kernel[1, 1] + b * sepia_kernel[1, 2]
        new_b = r * sepia_kernel[2, 0] + g * sepia_kernel[2, 1] + b * sepia_kernel[2, 2]
        result[..., 0] = np.clip(new_b, 0, 255)
        result[..., 1] = np.clip(new_g, 0, 255)
        result[..., 2] = np.clip(new_r, 0, 255)

        # Vignette
        h, w = image.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        radius = max(cx, cy)
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / radius
        vignette = np.clip(1.0 - dist * 0.5, 0.3, 1.0)
        result *= vignette[..., np.newaxis]

        return np.clip(result, 0, 255).astype(np.uint8)

    def _grade_high_contrast(self, image: np.ndarray) -> np.ndarray:
        """Increase contrast via CLAHE, boost saturation."""
        # CLAHE on L channel of LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        lab[..., 0] = clahe.apply(lab[..., 0])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Boost saturation in HSV
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float64)
        hsv[..., 1] = np.clip(hsv[..., 1] * 1.3, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    def _grade_bw_dramatic(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale with high contrast CLAHE."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        dramatic = clahe.apply(gray)
        return cv2.cvtColor(dramatic, cv2.COLOR_GRAY2BGR)

    # ------------------------------------------------------------------
    # Subtitle Burn
    # ------------------------------------------------------------------
    async def subtitle_burn(
        self,
        image: np.ndarray,
        text: str,
        position: str = "bottom",
        font_scale: float = 1.0,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> np.ndarray:
        """Add text with background box at specified position.

        Positions: 'top', 'center', 'bottom'.
        """
        result = image.copy()
        h, w = result.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(font_scale * 2))

        # Measure text size
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # Determine position
        margin = 10
        if position == "top":
            text_x = (w - text_w) // 2
            text_y = text_h + margin + baseline
        elif position == "center":
            text_x = (w - text_w) // 2
            text_y = (h + text_h) // 2
        else:  # bottom
            text_x = (w - text_w) // 2
            text_y = h - margin - baseline

        # Draw background rectangle
        pad = 5
        bg_x1 = max(0, text_x - pad)
        bg_y1 = max(0, text_y - text_h - pad)
        bg_x2 = min(w, text_x + text_w + pad)
        bg_y2 = min(h, text_y + baseline + pad)
        cv2.rectangle(result, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)

        # Draw text
        cv2.putText(result, text, (text_x, text_y), font, font_scale, color, thickness)

        return result

    # ------------------------------------------------------------------
    # Create Highlight Clip
    # ------------------------------------------------------------------
    async def create_highlight_clip(
        self,
        frames: list[np.ndarray],
        scores: list[float],
        top_k: int = 5,
    ) -> list[int]:
        """Return indices of top_k highest-scoring frames.

        Scores could represent motion magnitude, detection count, etc.
        """
        if not scores:
            return []

        k = min(top_k, len(scores))
        indices = np.argsort(scores)[-k:][::-1]
        return sorted(indices.tolist())
