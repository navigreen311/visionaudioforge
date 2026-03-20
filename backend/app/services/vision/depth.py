"""Depth estimation service using monocular depth approximation."""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class DepthEstimator:
    """Monocular depth estimation using gradient-based approximation.

    V1 uses Laplacian-based gradient magnitude as a proxy for relative depth.
    V2 target: integrate MiDaS model for real monocular depth estimation.
    """

    def estimate_depth(
        self,
        image: np.ndarray,
        method: str = "relative",
    ) -> dict:
        """Estimate depth from a single image.

        Parameters
        ----------
        image : np.ndarray
            BGR input image.
        method : str
            Depth estimation method. Currently only 'relative' is supported.

        Returns
        -------
        dict with keys:
            depth_map : np.ndarray (float32, 0-1 normalized)
            min_depth : float
            max_depth : float
            visualization : np.ndarray (colormap applied)
        """
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Compute Laplacian (gradient magnitude) as depth proxy
        # Higher gradient magnitude → closer objects (more texture/detail)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        gradient_mag = np.abs(laplacian).astype(np.float32)

        # Apply Gaussian blur to smooth the depth map
        gradient_mag = cv2.GaussianBlur(gradient_mag, (15, 15), 0)

        # Normalize to 0-1 range
        min_val = float(gradient_mag.min())
        max_val = float(gradient_mag.max())
        if max_val - min_val > 1e-6:
            depth_map = (gradient_mag - min_val) / (max_val - min_val)
        else:
            depth_map = np.zeros_like(gradient_mag)

        depth_map = depth_map.astype(np.float32)

        # Create visualization with COLORMAP_MAGMA
        vis_uint8 = (depth_map * 255).astype(np.uint8)
        visualization = cv2.applyColorMap(vis_uint8, cv2.COLORMAP_MAGMA)

        return {
            "depth_map": depth_map,
            "min_depth": float(depth_map.min()),
            "max_depth": float(depth_map.max()),
            "visualization": visualization,
        }

    def depth_to_pointcloud_stub(
        self,
        depth_map: np.ndarray,
        camera_intrinsics: dict | None = None,
    ) -> dict:
        """Stub for 3D point cloud generation from depth map.

        V2 target: implement real point cloud generation with camera calibration.

        Parameters
        ----------
        depth_map : np.ndarray
            Depth map (H x W, float32).
        camera_intrinsics : dict or None
            Camera calibration parameters (fx, fy, cx, cy).

        Returns
        -------
        dict with point count and status note.
        """
        points = int(depth_map.size) if depth_map is not None else 0
        return {
            "points": points,
            "note": "Real 3D requires camera calibration",
        }
