"""Visualization utilities for optical flow and motion analysis."""

from __future__ import annotations

import cv2
import numpy as np


def draw_optical_flow_arrows(
    frame: np.ndarray,
    old_pts: np.ndarray,
    new_pts: np.ndarray,
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
) -> np.ndarray:
    """Draw arrows from old to new tracked points on a copy of the frame."""
    output = frame.copy()
    if len(old_pts) == 0:
        return output

    for old, new in zip(old_pts.reshape(-1, 2), new_pts.reshape(-1, 2)):
        a, b = int(new[0]), int(new[1])
        c, d = int(old[0]), int(old[1])
        output = cv2.arrowedLine(output, (c, d), (a, b), color, thickness, tipLength=0.3)
        output = cv2.circle(output, (a, b), 3, color, -1)

    return output


def create_motion_heatmap(flow: np.ndarray) -> np.ndarray:
    """Create an HSV heatmap from dense optical flow.

    Hue encodes direction, value encodes magnitude (normalized),
    saturation is fixed at 255.
    """
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    hsv = np.zeros((*flow.shape[:2], 3), dtype=np.uint8)
    hsv[..., 0] = (angle * 180 / np.pi / 2).astype(np.uint8)  # Hue
    hsv[..., 1] = 255  # Saturation
    max_mag = magnitude.max()
    if max_mag > 0:
        hsv[..., 2] = (cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)).astype(
            np.uint8
        )
    else:
        hsv[..., 2] = 0

    return hsv


def create_flow_visualization(flow: np.ndarray) -> np.ndarray:
    """Convert dense optical flow to an RGB image using HSV encoding."""
    hsv = create_motion_heatmap(flow)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return rgb


def draw_motion_mask_overlay(
    frame: np.ndarray,
    mask: np.ndarray,
    color: tuple[int, int, int] = (0, 0, 255),
    alpha: float = 0.4,
) -> np.ndarray:
    """Overlay colored mask on frame where motion is detected."""
    output = frame.copy()

    # Ensure frame is 3-channel
    if len(output.shape) == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)

    # Create colored overlay
    overlay = output.copy()
    overlay[mask > 0] = color

    # Blend
    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
    return output
