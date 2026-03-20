"""Screen intelligence service for screenshot and UI analysis."""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ScreenIntelligence:
    """Analyze screenshots for UI elements, layout, and content.

    V1 uses contour detection, heuristics, and Hough transforms.
    """

    def analyze_screenshot(self, image: np.ndarray) -> dict:
        """Full analysis of a screenshot image.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.

        Returns
        -------
        dict with keys:
            ui_elements : list of detected UI elements
            text_content : str (OCR text if available)
            brightness : float (0-255)
            edge_density : float (0-1)
            dominant_colors : list of [B, G, R] values
            layout_type : str
        """
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]

        # Brightness
        brightness = float(np.mean(gray))

        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / (h * w)

        # Dominant colors (k-means with k=5)
        dominant_colors = self._extract_dominant_colors(image, k=5)

        # UI elements
        ui_elements = self.detect_ui_elements(image)

        # Text content via OCR (best effort)
        text_content = self._extract_text(image)

        # Layout classification
        layout_type = self._classify_layout(ui_elements, h, w)

        return {
            "ui_elements": ui_elements,
            "text_content": text_content,
            "brightness": round(brightness, 2),
            "edge_density": round(edge_density, 4),
            "dominant_colors": dominant_colors,
            "layout_type": layout_type,
        }

    def detect_ui_elements(self, image: np.ndarray) -> list[dict]:
        """Detect UI elements using contour analysis and heuristics.

        Classifies elements by size, aspect ratio, and position:
        - Small rectangles with moderate aspect ratio → buttons
        - Wide, short rectangles → inputs
        - Large blocks → images
        - Small elements → text
        - Vertical tall elements → menus

        Parameters
        ----------
        image : np.ndarray
            BGR input image.

        Returns
        -------
        list of dicts with keys: type, bbox [x, y, w, h], confidence.
        """
        if image is None or image.size == 0:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h_img, w_img = gray.shape[:2]
        img_area = h_img * w_img

        # Edge detection and contour finding
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        elements: list[dict] = []
        min_area = img_area * 0.001  # Ignore tiny contours
        max_area = img_area * 0.8  # Ignore full-image contours

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if area < min_area or area > max_area:
                continue

            aspect_ratio = w / max(h, 1)
            area_ratio = area / img_area

            # Classify by shape heuristics
            element_type, confidence = self._classify_element(
                w, h, aspect_ratio, area_ratio, x, y, w_img, h_img
            )

            elements.append({
                "type": element_type,
                "bbox": [int(x), int(y), int(w), int(h)],
                "confidence": round(confidence, 2),
            })

        return elements

    def parse_chart(self, image: np.ndarray) -> dict:
        """Detect and parse chart structures in an image.

        V1 uses Hough line transform for axis detection and
        shape patterns for chart type classification.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.

        Returns
        -------
        dict with keys:
            chart_type : str or None
            has_axes : bool
            data_regions : list of bbox [x, y, w, h]
        """
        if image is None or image.size == 0:
            return {"chart_type": None, "has_axes": False, "data_regions": []}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        edges = cv2.Canny(gray, 50, 150)

        # Detect lines with Hough transform
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=50,
            minLineLength=min(w, h) // 4, maxLineGap=10,
        )

        has_axes = False
        horizontal_lines: list = []
        vertical_lines: list = []

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))

                if angle < 10 or angle > 170:  # Horizontal
                    horizontal_lines.append(line[0])
                elif 80 < angle < 100:  # Vertical
                    vertical_lines.append(line[0])

            # Axes typically = one horizontal + one vertical near edges
            if horizontal_lines and vertical_lines:
                has_axes = True

        # Detect chart type from shape patterns
        chart_type = self._classify_chart_type(gray, edges, has_axes)

        # Find data regions (non-white, non-background areas)
        data_regions = self._find_data_regions(gray)

        return {
            "chart_type": chart_type,
            "has_axes": has_axes,
            "data_regions": data_regions,
        }

    def track_cursor(self, frames: list[np.ndarray]) -> list[dict]:
        """Track cursor/pointer position across frames.

        V1 uses shape detection to find small arrow/pointer shapes.

        Parameters
        ----------
        frames : list of np.ndarray
            Sequence of BGR frames.

        Returns
        -------
        list of dicts with keys: frame (int), position [x, y], clicked (bool).
        """
        results: list[dict] = []

        prev_gray = None
        for idx, frame in enumerate(frames):
            if frame is None or frame.size == 0:
                results.append({
                    "frame": idx,
                    "position": [0, 0],
                    "clicked": False,
                })
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

            # Detect cursor-like small bright/dark features
            position = self._detect_cursor_position(gray)

            # Simple click detection: compare with previous frame
            clicked = False
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(prev_gray, gray)
                # A click often causes a localized change near cursor
                if position[0] > 0 and position[1] > 0:
                    h, w = gray.shape[:2]
                    cx, cy = position
                    rx1 = max(0, cx - 20)
                    ry1 = max(0, cy - 20)
                    rx2 = min(w, cx + 20)
                    ry2 = min(h, cy + 20)
                    local_diff = diff[ry1:ry2, rx1:rx2]
                    if local_diff.size > 0 and float(np.mean(local_diff)) > 15:
                        clicked = True

            results.append({
                "frame": idx,
                "position": position,
                "clicked": clicked,
            })
            prev_gray = gray

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_element(
        w: int, h: int, aspect_ratio: float, area_ratio: float,
        x: int, y: int, img_w: int, img_h: int,
    ) -> tuple[str, float]:
        """Classify a UI element by its geometric properties."""
        # Large area → image region
        if area_ratio > 0.15:
            return "image", 0.6

        # Tall, narrow at edge → menu/sidebar
        if aspect_ratio < 0.3 and h > img_h * 0.3 and (x < img_w * 0.15 or x > img_w * 0.85):
            return "menu", 0.65

        # Wide, short → input field
        if 3.0 < aspect_ratio < 15.0 and h < img_h * 0.08:
            return "input", 0.6

        # Small-medium rectangle → button
        if 0.5 < aspect_ratio < 5.0 and 0.002 < area_ratio < 0.05:
            return "button", 0.55

        # Default → text region
        return "text", 0.4

    @staticmethod
    def _extract_dominant_colors(image: np.ndarray, k: int = 5) -> list[list[int]]:
        """Extract dominant colors using k-means clustering."""
        if len(image.shape) < 3:
            mean_val = int(np.mean(image))
            return [[mean_val, mean_val, mean_val]]

        # Downsample for speed
        small = cv2.resize(image, (64, 64))
        pixels = small.reshape(-1, 3).astype(np.float32)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )

        # Sort by frequency
        label_counts = np.bincount(labels.flatten())
        sorted_indices = np.argsort(-label_counts)

        colors = []
        for idx in sorted_indices:
            color = centers[idx].astype(int).tolist()
            colors.append(color)

        return colors

    @staticmethod
    def _extract_text(image: np.ndarray) -> str:
        """Extract text from image using pytesseract if available."""
        try:
            import pytesseract

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except ImportError:
            return ""
        except Exception:
            logger.debug("OCR text extraction failed")
            return ""

    @staticmethod
    def _classify_layout(elements: list[dict], h: int, w: int) -> str:
        """Classify the overall layout type from detected elements."""
        if not elements:
            return "unknown"

        has_sidebar = any(
            e["type"] == "menu" for e in elements
        )
        button_count = sum(1 for e in elements if e["type"] == "button")
        input_count = sum(1 for e in elements if e["type"] == "input")
        image_count = sum(1 for e in elements if e["type"] == "image")

        if has_sidebar:
            return "dashboard"
        if input_count >= 3:
            return "form"
        if image_count >= 2:
            return "gallery"
        if button_count >= 3:
            return "toolbar"

        return "content"

    @staticmethod
    def _classify_chart_type(
        gray: np.ndarray, edges: np.ndarray, has_axes: bool,
    ) -> str | None:
        """Classify chart type from visual features."""
        if not has_axes:
            # Check for pie chart (circular shape)
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, 1, 50,
                param1=100, param2=30,
                minRadius=min(gray.shape) // 6,
                maxRadius=min(gray.shape) // 2,
            )
            if circles is not None:
                return "pie"
            return None

        # With axes: detect bar vs line
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tall_rects = 0
        thin_shapes = 0

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if area < 100:
                continue
            aspect = h / max(w, 1)

            if aspect > 2.0 and w < gray.shape[1] * 0.15:
                tall_rects += 1
            elif aspect < 0.3:
                thin_shapes += 1

        if tall_rects >= 3:
            return "bar"
        if thin_shapes >= 2:
            return "line"

        return "unknown"

    @staticmethod
    def _find_data_regions(gray: np.ndarray) -> list[list[int]]:
        """Find data-containing regions in a chart."""
        # Threshold to find non-background regions
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[list[int]] = []
        img_area = gray.shape[0] * gray.shape[1]

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if area > img_area * 0.01 and area < img_area * 0.8:
                regions.append([int(x), int(y), int(w), int(h)])

        return regions

    @staticmethod
    def _detect_cursor_position(gray: np.ndarray) -> list[int]:
        """Detect cursor position using small bright feature detection."""
        h, w = gray.shape[:2]

        # Look for small, bright/contrasting features that could be a cursor
        # Apply adaptive threshold to find small distinct objects
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for cursor-sized contours (small, roughly triangular)
        cursor_candidates: list[tuple[int, int, float]] = []
        for c in contours:
            area = cv2.contourArea(c)
            if 20 < area < 500:  # Cursor-sized
                M = cv2.moments(c)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cursor_candidates.append((cx, cy, area))

        if cursor_candidates:
            # Return the most likely cursor (smallest qualifying contour)
            cursor_candidates.sort(key=lambda c: c[2])
            return [cursor_candidates[0][0], cursor_candidates[0][1]]

        return [0, 0]
