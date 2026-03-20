"""Motion analysis service: optical flow and frame differencing."""

from __future__ import annotations

import cv2
import numpy as np


class MotionAnalyzer:
    """Stateful motion analysis with Lucas-Kanade, Farneback, and frame differencing."""

    # -- Sparse optical flow (Lucas-Kanade) --------------------------------

    @staticmethod
    def lucas_kanade(
        prev_gray: np.ndarray,
        curr_gray: np.ndarray,
        feature_params: dict | None = None,
        lk_params: dict | None = None,
    ) -> dict:
        """Compute sparse optical flow using Lucas-Kanade method.

        Returns dict with tracked_points, motion_vectors, magnitudes,
        mean_magnitude, and num_tracked.
        """
        if feature_params is None:
            feature_params = dict(
                maxCorners=100,
                qualityLevel=0.3,
                minDistance=7,
                blockSize=7,
            )

        if lk_params is None:
            criteria = (
                cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                10,
                0.03,
            )
            lk_params = dict(
                winSize=(15, 15),
                maxLevel=2,
                criteria=criteria,
            )

        # Detect good features to track in previous frame
        old_pts = cv2.goodFeaturesToTrack(prev_gray, **feature_params)

        if old_pts is None or len(old_pts) == 0:
            return {
                "tracked_points": {"old": np.array([]), "new": np.array([])},
                "motion_vectors": np.array([]),
                "magnitudes": np.array([]),
                "mean_magnitude": 0.0,
                "num_tracked": 0,
            }

        # Calculate optical flow
        new_pts, status, _err = cv2.calcOpticalFlowPyrLK(
            prev_gray, curr_gray, old_pts, None, **lk_params
        )

        # Filter only successfully tracked points
        good_mask = status.ravel() == 1
        old_good = old_pts[good_mask]
        new_good = new_pts[good_mask]

        # Compute motion vectors and magnitudes
        motion_vectors = new_good - old_good
        magnitudes = np.sqrt(
            motion_vectors[:, :, 0] ** 2 + motion_vectors[:, :, 1] ** 2
        ).ravel()

        return {
            "tracked_points": {"old": old_good, "new": new_good},
            "motion_vectors": motion_vectors,
            "magnitudes": magnitudes,
            "mean_magnitude": float(np.mean(magnitudes)) if len(magnitudes) > 0 else 0.0,
            "num_tracked": int(len(old_good)),
        }

    # -- Dense optical flow (Farneback) ------------------------------------

    @staticmethod
    def farneback_dense(
        prev_gray: np.ndarray,
        curr_gray: np.ndarray,
        params: dict | None = None,
    ) -> dict:
        """Compute dense optical flow using Farneback method.

        Returns dict with flow array (h,w,2), magnitude, angle,
        mean_magnitude, and max_magnitude.
        """
        if params is None:
            params = dict(
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0,
            )

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            curr_gray,
            None,
            params["pyr_scale"],
            params["levels"],
            params["winsize"],
            params["iterations"],
            params["poly_n"],
            params["poly_sigma"],
            params["flags"],
        )

        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        return {
            "flow": flow,
            "magnitude": magnitude,
            "angle": angle,
            "mean_magnitude": float(np.mean(magnitude)),
            "max_magnitude": float(np.max(magnitude)),
        }

    # -- Frame differencing ------------------------------------------------

    @staticmethod
    def frame_diff_consecutive(
        prev_gray: np.ndarray,
        curr_gray: np.ndarray,
        threshold: int = 25,
    ) -> dict:
        """Two-frame differencing with morphological cleanup.

        Returns dict with motion_mask, motion_percentage, motion_pixels,
        and total_pixels.
        """
        diff = cv2.absdiff(prev_gray, curr_gray)
        _, thresh_img = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

        # Morphological opening to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        motion_mask = cv2.morphologyEx(thresh_img, cv2.MORPH_OPEN, kernel)

        motion_pixels = int(cv2.countNonZero(motion_mask))
        total_pixels = int(motion_mask.shape[0] * motion_mask.shape[1])
        motion_pct = (motion_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

        return {
            "motion_mask": motion_mask,
            "motion_percentage": motion_pct,
            "motion_pixels": motion_pixels,
            "total_pixels": total_pixels,
        }

    @staticmethod
    def frame_diff_three_frame(
        f1_gray: np.ndarray,
        f2_gray: np.ndarray,
        f3_gray: np.ndarray,
        threshold: int = 25,
    ) -> dict:
        """Three-frame differencing for robust motion detection.

        Computes diff between (f1,f2) and (f2,f3), then bitwise AND
        of the two thresholded results.
        """
        diff1 = cv2.absdiff(f1_gray, f2_gray)
        diff2 = cv2.absdiff(f2_gray, f3_gray)

        _, thresh1 = cv2.threshold(diff1, threshold, 255, cv2.THRESH_BINARY)
        _, thresh2 = cv2.threshold(diff2, threshold, 255, cv2.THRESH_BINARY)

        motion_mask = cv2.bitwise_and(thresh1, thresh2)

        total_pixels = int(motion_mask.shape[0] * motion_mask.shape[1])
        motion_pixels = int(cv2.countNonZero(motion_mask))
        motion_pct = (motion_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

        return {
            "motion_mask": motion_mask,
            "motion_percentage": motion_pct,
        }

    # -- Statistics --------------------------------------------------------

    @staticmethod
    def compute_motion_stats(motion_data: dict) -> dict:
        """Compute summary statistics from motion analysis results.

        Accepts output from lucas_kanade, farneback_dense, or frame_diff
        and returns unified stats dict.
        """
        stats: dict = {
            "mean_magnitude": 0.0,
            "max_magnitude": 0.0,
            "motion_area_pct": 0.0,
            "dominant_direction_deg": 0.0,
        }

        # From Farneback dense flow
        if "flow" in motion_data:
            flow = motion_data["flow"]
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            stats["mean_magnitude"] = float(np.mean(mag))
            stats["max_magnitude"] = float(np.max(mag))
            # Motion area: percentage of pixels with magnitude > 1.0
            stats["motion_area_pct"] = float(np.sum(mag > 1.0) / mag.size * 100.0)
            # Dominant direction: angle of highest average magnitude
            stats["dominant_direction_deg"] = float(
                np.degrees(ang.ravel()[np.argmax(mag.ravel())])
            )

        # From Lucas-Kanade sparse flow
        elif "magnitudes" in motion_data and len(motion_data["magnitudes"]) > 0:
            mags = motion_data["magnitudes"]
            vectors = motion_data["motion_vectors"]
            stats["mean_magnitude"] = float(np.mean(mags))
            stats["max_magnitude"] = float(np.max(mags))
            stats["motion_area_pct"] = 0.0  # sparse — not applicable
            if len(vectors) > 0:
                mean_vec = np.mean(vectors.reshape(-1, 2), axis=0)
                stats["dominant_direction_deg"] = float(
                    np.degrees(np.arctan2(mean_vec[1], mean_vec[0]))
                )

        # From frame differencing
        elif "motion_mask" in motion_data:
            stats["motion_area_pct"] = motion_data.get("motion_percentage", 0.0)

        return stats
