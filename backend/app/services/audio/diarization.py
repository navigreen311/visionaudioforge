"""Speaker diarization using energy-based segmentation and spectral clustering."""

from __future__ import annotations

import numpy as np


class SpeakerDiarizer:
    """Identify and segment speakers in audio using MFCC clustering."""

    def diarize(
        self,
        audio: np.ndarray,
        sr: int,
        num_speakers: int | None = None,
    ) -> dict:
        """Diarize audio into speaker segments.

        Uses energy-based segmentation with MFCC features and KMeans clustering.

        Returns dict with keys: segments, num_speakers, speaker_stats.
        """
        import librosa
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        duration_s = len(audio) / sr

        # Split audio into 1-second frames
        frame_len = sr  # 1 second per frame
        n_frames = max(1, len(audio) // frame_len)

        if n_frames < 2:
            # Too short for meaningful diarization
            return {
                "segments": [
                    {
                        "speaker": "Speaker_0",
                        "start_s": 0.0,
                        "end_s": round(duration_s, 3),
                        "duration_s": round(duration_s, 3),
                    }
                ],
                "num_speakers": 1,
                "speaker_stats": {
                    "Speaker_0": {
                        "total_time": round(duration_s, 3),
                        "percentage": 100.0,
                        "avg_energy": float(np.sqrt(np.mean(audio**2))),
                    }
                },
            }

        # Compute MFCC per frame
        mfcc_features = []
        frame_energies = []
        for i in range(n_frames):
            frame = audio[i * frame_len : (i + 1) * frame_len]
            energy = float(np.sqrt(np.mean(frame**2)))
            frame_energies.append(energy)

            # Compute MFCCs for this frame
            mfcc = librosa.feature.mfcc(y=frame, sr=sr, n_mfcc=13)
            # Use mean of each coefficient across the frame as feature vector
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_features.append(mfcc_mean)

        feature_matrix = np.array(mfcc_features)

        # Determine number of speakers
        if num_speakers is not None:
            k = max(1, min(num_speakers, n_frames))
        else:
            # Auto-detect using silhouette score (try 2-5 speakers)
            max_k = min(5, n_frames)
            if max_k < 2:
                k = 1
            else:
                best_k = 2
                best_score = -1.0
                for candidate_k in range(2, max_k + 1):
                    km = KMeans(n_clusters=candidate_k, random_state=42, n_init=10)
                    labels = km.fit_predict(feature_matrix)
                    if len(set(labels)) < 2:
                        continue
                    score = silhouette_score(feature_matrix, labels)
                    if score > best_score:
                        best_score = score
                        best_k = candidate_k
                k = best_k

        if k <= 1:
            labels = np.zeros(n_frames, dtype=int)
        else:
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(feature_matrix)

        # Merge consecutive frames with same speaker label
        segments: list[dict] = []
        current_label = int(labels[0])
        current_start = 0.0

        for i in range(1, n_frames):
            if int(labels[i]) != current_label:
                end_s = float(i)
                segments.append(
                    {
                        "speaker": f"Speaker_{current_label}",
                        "start_s": round(current_start, 3),
                        "end_s": round(end_s, 3),
                        "duration_s": round(end_s - current_start, 3),
                    }
                )
                current_label = int(labels[i])
                current_start = float(i)

        # Close last segment
        end_s = min(float(n_frames), duration_s)
        segments.append(
            {
                "speaker": f"Speaker_{current_label}",
                "start_s": round(current_start, 3),
                "end_s": round(end_s, 3),
                "duration_s": round(end_s - current_start, 3),
            }
        )

        # Compute speaker stats
        actual_speakers = set(int(l) for l in labels)
        speaker_stats: dict[str, dict] = {}

        for spk_id in sorted(actual_speakers):
            mask = labels == spk_id
            total_time = float(np.sum(mask))  # each frame is 1 second
            percentage = round(total_time / n_frames * 100.0, 2)
            spk_energies = [frame_energies[i] for i in range(n_frames) if mask[i]]
            avg_energy = float(np.mean(spk_energies)) if spk_energies else 0.0

            speaker_stats[f"Speaker_{spk_id}"] = {
                "total_time": round(total_time, 3),
                "percentage": percentage,
                "avg_energy": round(avg_energy, 6),
            }

        return {
            "segments": segments,
            "num_speakers": len(actual_speakers),
            "speaker_stats": speaker_stats,
        }

    def get_speaker_transcript(
        self,
        diarization: dict,
        transcription: dict,
    ) -> list[dict]:
        """Align STT segments with diarization segments by time overlap.

        Args:
            diarization: Result from diarize() with 'segments' key.
            transcription: Result from STT with 'segments' key containing
                           dicts with 'start', 'end', 'text'.

        Returns:
            List of dicts with speaker, text, start_s, end_s.
        """
        diar_segments = diarization.get("segments", [])
        trans_segments = transcription.get("segments", [])

        if not diar_segments or not trans_segments:
            return []

        result: list[dict] = []

        for tseg in trans_segments:
            t_start = tseg.get("start", 0.0)
            t_end = tseg.get("end", 0.0)
            text = tseg.get("text", "")

            # Find the diarization segment with the greatest overlap
            best_speaker = diar_segments[0]["speaker"]
            best_overlap = 0.0

            for dseg in diar_segments:
                overlap_start = max(t_start, dseg["start_s"])
                overlap_end = min(t_end, dseg["end_s"])
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = dseg["speaker"]

            result.append(
                {
                    "speaker": best_speaker,
                    "text": text.strip(),
                    "start_s": round(t_start, 3),
                    "end_s": round(t_end, 3),
                }
            )

        return result
