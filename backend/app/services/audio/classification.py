"""Audio classification and anomaly detection via spectral heuristics."""

from __future__ import annotations

import numpy as np
import librosa


class AudioClassifier:
    """Classify audio content and detect anomalies using spectral features."""

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_sound(
        self,
        audio: np.ndarray,
        sr: int,
        categories: list[str] | None = None,
    ) -> dict:
        """Classify audio into a category using MFCC / spectral heuristics.

        Returns dict with keys: category, confidence, all_scores.
        """
        if categories is None:
            categories = ["silence", "speech", "music", "noise"]

        rms = float(np.sqrt(np.mean(audio ** 2)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
        spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_var = float(np.mean(np.var(mfccs, axis=1)))

        scores: dict[str, float] = {cat: 0.0 for cat in categories}

        # Silence: low energy + high zero-crossing rate
        if "silence" in scores:
            if rms < 0.01:
                scores["silence"] = 0.95
            elif rms < 0.05:
                scores["silence"] = 0.4
            else:
                scores["silence"] = 0.05

        # Speech: moderate energy, voice-range centroid (300-3000 Hz), periodic
        if "speech" in scores:
            voice_range = 300 < spectral_centroid < 3000
            moderate_energy = 0.01 <= rms <= 0.8
            if voice_range and moderate_energy:
                scores["speech"] = 0.7 + min(0.2, mfcc_var * 0.01)
            elif voice_range:
                scores["speech"] = 0.4
            else:
                scores["speech"] = 0.1

        # Music: broader spectrum, moderate-to-high energy, tonal
        if "music" in scores:
            if spectral_centroid > 1000 and rms > 0.05 and mfcc_var > 5:
                scores["music"] = 0.6
            else:
                scores["music"] = 0.15

        # Noise: high energy + broad spectrum + high zcr
        if "noise" in scores:
            if rms > 0.1 and zcr > 0.1 and spectral_centroid > 3000:
                scores["noise"] = 0.7
            elif zcr > 0.2:
                scores["noise"] = 0.4
            else:
                scores["noise"] = 0.1

        # Normalize to sum to 1
        total = sum(scores.values()) or 1.0
        scores = {k: round(v / total, 4) for k, v in scores.items()}

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        return {
            "category": best,
            "confidence": scores[best],
            "all_scores": scores,
        }

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    def detect_anomaly(
        self,
        audio: np.ndarray,
        sr: int,
        reference_stats: dict | None = None,
    ) -> dict:
        """Flag audio as anomalous if features deviate significantly from reference.

        Returns dict with keys: is_anomaly, anomaly_score, reason.
        """
        rms = float(np.sqrt(np.mean(audio ** 2)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))

        if reference_stats is None:
            # No reference — cannot flag anomaly
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "reason": "no reference stats provided",
            }

        deviations: list[tuple[str, float]] = []
        for feat_name, feat_val in [("rms", rms), ("zcr", zcr), ("spectral_centroid", centroid)]:
            ref = reference_stats.get(feat_name)
            if ref is None:
                continue
            mean = ref.get("mean", 0.0)
            std = ref.get("std", 1.0)
            if std == 0:
                std = 1e-10
            z = abs(feat_val - mean) / std
            deviations.append((feat_name, z))

        if not deviations:
            return {"is_anomaly": False, "anomaly_score": 0.0, "reason": "no comparable stats"}

        max_feat, max_z = max(deviations, key=lambda x: x[1])
        is_anomaly = max_z > 3.0

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(float(max_z), 4),
            "reason": f"{max_feat} deviated {max_z:.2f} std from reference" if is_anomaly else "within normal range",
        }
