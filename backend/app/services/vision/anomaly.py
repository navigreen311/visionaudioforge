"""Anomaly detection service for images using statistical methods."""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Statistical anomaly detection for images.

    Compares images against reference statistics or absolute thresholds
    to identify anomalous frames (too dark, too bright, low contrast,
    color cast, etc.).
    """

    # Absolute thresholds for self-check (no reference)
    DARK_THRESHOLD = 20
    BRIGHT_THRESHOLD = 235
    LOW_CONTRAST_STD = 10

    def detect_anomaly(
        self,
        image: np.ndarray,
        reference_images: list[np.ndarray] | None = None,
        method: str = "statistical",
    ) -> dict:
        """Detect anomalies in a single image.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.
        reference_images : list[np.ndarray] or None
            Optional reference images for comparison.
        method : str
            Detection method. Currently only 'statistical' is supported.

        Returns
        -------
        dict with keys:
            is_anomaly : bool
            anomaly_score : float (0-1)
            anomaly_regions : list[list[int]] (bounding boxes)
            reason : str
        """
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        img_mean = float(np.mean(gray))
        img_std = float(np.std(gray))

        reasons: list[str] = []
        anomaly_score = 0.0
        anomaly_regions: list[list[int]] = []

        if reference_images and len(reference_images) > 0:
            ref_stats = self.build_reference_stats(reference_images)
            ref_mean = float(ref_stats["mean"])
            ref_std = float(ref_stats["std"]) if ref_stats["std"] > 0 else 1.0

            z_score = abs(img_mean - ref_mean) / ref_std
            if z_score > 3.0:
                reasons.append(
                    f"Mean intensity deviates {z_score:.1f} std devs from reference"
                )
                anomaly_score = min(1.0, z_score / 6.0)
        else:
            # Absolute threshold checks
            if img_mean < self.DARK_THRESHOLD:
                reasons.append(f"Image too dark (mean={img_mean:.1f})")
                anomaly_score = max(anomaly_score, 1.0 - img_mean / self.DARK_THRESHOLD)

            if img_mean > self.BRIGHT_THRESHOLD:
                reasons.append(f"Image too bright (mean={img_mean:.1f})")
                anomaly_score = max(
                    anomaly_score,
                    (img_mean - self.BRIGHT_THRESHOLD) / (255 - self.BRIGHT_THRESHOLD),
                )

            if img_std < self.LOW_CONTRAST_STD:
                reasons.append(f"Low contrast (std={img_std:.1f})")
                anomaly_score = max(
                    anomaly_score, 1.0 - img_std / self.LOW_CONTRAST_STD
                )

            # Color cast detection (for color images)
            if len(image.shape) == 3 and image.shape[2] == 3:
                channel_means = [float(np.mean(image[:, :, c])) for c in range(3)]
                overall_mean = sum(channel_means) / 3.0
                for i, (ch_mean, ch_name) in enumerate(
                    zip(channel_means, ["Blue", "Green", "Red"])
                ):
                    if overall_mean > 10 and abs(ch_mean - overall_mean) > 50:
                        reasons.append(
                            f"{ch_name} color cast (channel mean={ch_mean:.1f}, "
                            f"overall={overall_mean:.1f})"
                        )
                        deviation = abs(ch_mean - overall_mean) / 128.0
                        anomaly_score = max(anomaly_score, min(1.0, deviation))

        # Detect anomaly regions using local statistics
        if anomaly_score > 0.3:
            h, w = gray.shape[:2]
            block_h, block_w = max(1, h // 4), max(1, w // 4)
            for by in range(4):
                for bx in range(4):
                    y1, y2 = by * block_h, min((by + 1) * block_h, h)
                    x1, x2 = bx * block_w, min((bx + 1) * block_w, w)
                    block = gray[y1:y2, x1:x2]
                    block_mean = float(np.mean(block))
                    if block_mean < self.DARK_THRESHOLD or block_mean > self.BRIGHT_THRESHOLD:
                        anomaly_regions.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])

        is_anomaly = anomaly_score > 0.3
        reason = "; ".join(reasons) if reasons else "Normal"

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(float(anomaly_score), 4),
            "anomaly_regions": anomaly_regions,
            "reason": reason,
        }

    def detect_anomaly_batch(
        self,
        images: list[np.ndarray],
        reference_stats: dict | None = None,
    ) -> list[dict]:
        """Detect anomalies in a batch of images.

        Parameters
        ----------
        images : list[np.ndarray]
            List of BGR images.
        reference_stats : dict or None
            Pre-computed reference statistics from build_reference_stats().

        Returns
        -------
        list of anomaly result dicts.
        """
        results = []
        for img in images:
            results.append(self.detect_anomaly(img))
        return results

    def build_reference_stats(
        self,
        images: list[np.ndarray],
    ) -> dict:
        """Build reference statistics from multiple images.

        Parameters
        ----------
        images : list[np.ndarray]
            List of reference images (BGR).

        Returns
        -------
        dict with keys: mean, std, histogram
        """
        if not images:
            return {"mean": np.float64(0), "std": np.float64(0), "histogram": np.zeros(256)}

        means = []
        all_histograms = []

        for img in images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            means.append(float(np.mean(gray)))
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
            all_histograms.append(hist)

        mean_val = np.mean(means)
        std_val = np.std(means) if len(means) > 1 else np.float64(0)
        avg_histogram = np.mean(all_histograms, axis=0)

        return {
            "mean": mean_val,
            "std": std_val,
            "histogram": avg_histogram,
        }
