"""Audio fingerprinting service: generate and match acoustic fingerprints."""

from __future__ import annotations

import hashlib
from typing import Any

import librosa
import numpy as np
from scipy.ndimage import maximum_filter


class AudioFingerprinter:
    """Generate and compare audio fingerprints based on spectral peaks."""

    MATCH_THRESHOLD = 0.5  # >50 % peak-hash overlap for a match

    # ------------------------------------------------------------------
    # Peak detection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _find_peaks(spectrogram: np.ndarray, neighbourhood: int = 20) -> list[tuple[int, int]]:
        """Find local maxima in a 2-D spectrogram (freq × time).

        Returns list of (freq_bin, time_bin) tuples.
        """
        local_max = maximum_filter(spectrogram, size=neighbourhood)
        detected = (spectrogram == local_max) & (spectrogram > np.percentile(spectrogram, 75))
        freq_idx, time_idx = np.where(detected)
        return list(zip(freq_idx.tolist(), time_idx.tolist()))

    @staticmethod
    def _hash_peaks(peaks: list[tuple[int, int]], fan_value: int = 10) -> set[str]:
        """Create combinatorial hashes from peak pairs.

        Each hash encodes (freq1, freq2, time_delta).
        """
        peaks_sorted = sorted(peaks, key=lambda p: p[1])  # sort by time
        hashes: set[str] = set()
        for i, (f1, t1) in enumerate(peaks_sorted):
            for j in range(1, min(fan_value + 1, len(peaks_sorted) - i)):
                f2, t2 = peaks_sorted[i + j]
                dt = t2 - t1
                if dt <= 0:
                    continue
                h = hashlib.sha1(f"{f1}|{f2}|{dt}".encode()).hexdigest()[:16]
                hashes.add(h)
        return hashes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_fingerprint(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        """Generate an acoustic fingerprint for the given audio.

        Returns dict with *fingerprint* (hex string), *duration_s*, and *peaks* count.
        """
        S = np.abs(librosa.stft(audio))
        peaks = self._find_peaks(S)
        hashes = self._hash_peaks(peaks)

        # Combine all peak hashes into a single fingerprint string
        combined = "|".join(sorted(hashes))
        fp_hash = hashlib.sha256(combined.encode()).hexdigest()

        return {
            "fingerprint": fp_hash,
            "duration_s": round(len(audio) / sr, 4),
            "peaks": len(peaks),
            "_hashes": hashes,  # internal, used for matching
        }

    def match_fingerprints(self, fp1: dict, fp2: dict) -> dict[str, Any]:
        """Compare two fingerprints produced by *generate_fingerprint*.

        Returns match status, similarity score, and estimated offset.
        """
        h1: set[str] = fp1.get("_hashes", set())
        h2: set[str] = fp2.get("_hashes", set())

        if not h1 or not h2:
            return {"match": False, "similarity": 0.0, "offset_s": None}

        overlap = h1 & h2
        union = h1 | h2
        similarity = len(overlap) / len(union) if union else 0.0

        return {
            "match": similarity > self.MATCH_THRESHOLD,
            "similarity": round(similarity, 6),
            "offset_s": 0.0 if similarity > self.MATCH_THRESHOLD else None,
        }

    # ------------------------------------------------------------------
    # Fingerprint database helpers
    # ------------------------------------------------------------------
    @staticmethod
    def create_fingerprint_db() -> dict[str, dict]:
        """Return an empty fingerprint database (dict)."""
        return {}

    def search_fingerprint(
        self, query_fp: dict, db: dict[str, dict]
    ) -> dict[str, Any]:
        """Search for a matching fingerprint in *db*.

        Returns dict with *matched_id* and *confidence*.
        """
        best_id: str | None = None
        best_sim: float = 0.0

        for entry_id, stored_fp in db.items():
            result = self.match_fingerprints(query_fp, stored_fp)
            if result["similarity"] > best_sim:
                best_sim = result["similarity"]
                best_id = entry_id

        matched = best_id if best_sim > self.MATCH_THRESHOLD else None
        return {
            "matched_id": matched,
            "confidence": round(best_sim, 6),
        }
