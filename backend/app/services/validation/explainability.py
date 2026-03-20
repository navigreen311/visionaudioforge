"""ExplainabilityService — saliency maps, feature attribution, natural-language
explanations for model predictions."""

from __future__ import annotations

import base64
import io

import numpy as np


class ExplainabilityService:
    """V1 explainability utilities.  Full Grad-CAM requires model access;
    this version uses gradient-based saliency (Sobel) as a stand-in."""

    # ------------------------------------------------------------------
    # Saliency Map
    # ------------------------------------------------------------------

    @staticmethod
    async def compute_saliency_map(
        image: np.ndarray,
        model_output: dict | None = None,
    ) -> np.ndarray:
        """Compute a saliency heatmap for *image*.

        V1 implementation: Sobel gradient magnitude normalised to [0, 255].
        A real Grad-CAM implementation would back-propagate through the
        model's final conv layer — that requires runtime model access
        which is planned for V2.

        Parameters
        ----------
        image : np.ndarray
            Input image in HWC uint8 format (grayscale or RGB).
        model_output : dict, optional
            Model prediction metadata (unused in V1; reserved for Grad-CAM).

        Returns
        -------
        np.ndarray
            Heatmap of shape (H, W) with values in [0, 255] (uint8).
        """
        # Convert to grayscale if necessary
        if image.ndim == 3 and image.shape[2] == 3:
            gray = np.mean(image, axis=2).astype(np.float64)
        elif image.ndim == 3 and image.shape[2] == 1:
            gray = image[:, :, 0].astype(np.float64)
        else:
            gray = image.astype(np.float64)

        # Sobel kernels
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

        # Simple 2D convolution (no scipy dependency)
        def _conv2d(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
            kh, kw = kernel.shape
            ph, pw = kh // 2, kw // 2
            padded = np.pad(img, ((ph, ph), (pw, pw)), mode="reflect")
            out = np.zeros_like(img)
            for i in range(kh):
                for j in range(kw):
                    out += kernel[i, j] * padded[i : i + img.shape[0], j : j + img.shape[1]]
            return out

        gx = _conv2d(gray, sobel_x)
        gy = _conv2d(gray, sobel_y)
        magnitude = np.sqrt(gx ** 2 + gy ** 2)

        # Normalise to 0-255
        mag_min, mag_max = magnitude.min(), magnitude.max()
        if mag_max - mag_min > 0:
            heatmap = ((magnitude - mag_min) / (mag_max - mag_min) * 255).astype(np.uint8)
        else:
            heatmap = np.zeros_like(magnitude, dtype=np.uint8)

        return heatmap

    @staticmethod
    def heatmap_to_base64(heatmap: np.ndarray) -> str:
        """Encode a uint8 heatmap as a base64-encoded PNG string."""
        # Minimal PNG encoding without PIL: use raw grayscale BMP-like approach
        # For robustness we write a raw PGM (Portable GrayMap) and base64 it.
        h, w = heatmap.shape[:2]
        header = f"P5\n{w} {h}\n255\n".encode("ascii")
        buf = io.BytesIO()
        buf.write(header)
        buf.write(heatmap.tobytes())
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # ------------------------------------------------------------------
    # Feature Attribution
    # ------------------------------------------------------------------

    @staticmethod
    async def feature_attribution(
        features: dict[str, list[float]],
        predictions: list[float],
    ) -> list[dict]:
        """Estimate feature importance via correlation with prediction confidence.

        Returns a list sorted by descending absolute importance.
        """
        attributions: list[dict] = []
        n = len(predictions)

        if n < 2:
            return [{"feature": f, "importance": 0.0} for f in features]

        pred_mean = sum(predictions) / n
        pred_std = (sum((p - pred_mean) ** 2 for p in predictions) / n) ** 0.5

        for name, values in features.items():
            if len(values) != n:
                attributions.append({"feature": name, "importance": 0.0})
                continue

            feat_mean = sum(values) / n
            feat_std = (sum((v - feat_mean) ** 2 for v in values) / n) ** 0.5

            if feat_std == 0 or pred_std == 0:
                attributions.append({"feature": name, "importance": 0.0})
                continue

            cov = sum(
                (values[i] - feat_mean) * (predictions[i] - pred_mean) for i in range(n)
            ) / n
            correlation = cov / (feat_std * pred_std)
            attributions.append({"feature": name, "importance": round(correlation, 4)})

        attributions.sort(key=lambda a: abs(a["importance"]), reverse=True)
        return attributions

    # ------------------------------------------------------------------
    # Natural-Language Explanation
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_explanation(
        prediction: str | int,
        confidence: float,
        features: dict,
    ) -> dict:
        """Produce a human-readable explanation for a single prediction."""
        # Sort features by absolute value (proxy for importance)
        sorted_feats = sorted(
            features.items(),
            key=lambda kv: abs(kv[1]) if isinstance(kv[1], (int, float)) else 0,
            reverse=True,
        )
        top_factors = [
            {"feature": k, "value": v}
            for k, v in sorted_feats[:5]
        ]

        confidence_label = (
            "high" if confidence >= 0.8 else "moderate" if confidence >= 0.5 else "low"
        )

        factor_names = ", ".join(f["feature"] for f in top_factors[:3])
        explanation_text = (
            f"The model predicted '{prediction}' with {confidence_label} confidence "
            f"({confidence:.1%}). The top contributing factors were: {factor_names}."
        )

        return {
            "prediction": str(prediction),
            "confidence": round(confidence, 4),
            "top_factors": top_factors,
            "explanation_text": explanation_text,
        }
