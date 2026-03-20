"""Batch Transform Service — parallel processing of multiple files."""

from __future__ import annotations

import asyncio
import base64
import io
import traceback

import cv2
import numpy as np


class BatchTransformService:
    """Run audio or video transforms across multiple files in parallel."""

    async def batch_audio_transform(
        self,
        files: list[tuple[np.ndarray, int]],
        operations: list[dict],
    ) -> list[dict]:
        """Apply a sequence of operations to each audio file in parallel.

        Parameters
        ----------
        files : list of (audio_array, sample_rate) tuples
        operations : list of dicts, each with {"op": "<name>", ...params}

        Returns
        -------
        list of result dicts with status, audio (base64 WAV), and metadata.
        """
        from app.services.transform.audio_advanced import AdvancedAudioTransform
        from app.services.transform.audio_transform import AudioTransformService

        audio_svc = AudioTransformService()
        adv_audio = AdvancedAudioTransform()

        async def _process_one(audio: np.ndarray, sr: int) -> dict:
            result = audio.copy()
            applied: list[str] = []
            for op in operations:
                op_name = op.get("op", "")
                try:
                    if op_name == "denoise":
                        result = audio_svc.denoise(result, sr, method=op.get("method", "spectral_gating"))
                    elif op_name == "silence_remove":
                        result = audio_svc.remove_silence(result, sr)
                    elif op_name == "pitch_shift":
                        result = audio_svc.pitch_shift(result, sr, semitones=op.get("semitones", 0))
                    elif op_name == "time_stretch":
                        result = audio_svc.time_stretch(result, sr, rate=op.get("rate", 1.0))
                    elif op_name == "eq":
                        result = audio_svc.apply_eq(result, sr, preset=op.get("preset", "flat"))
                    elif op_name == "loudness":
                        result = audio_svc.normalize_loudness(result, sr, target_lufs=op.get("target_lufs", -14))
                    elif op_name == "voice_convert":
                        result = await adv_audio.voice_conversion_stub(result, sr, target_voice=op.get("target_voice", "male_deep"))
                    else:
                        continue
                    applied.append(op_name)
                except Exception:
                    applied.append(f"{op_name}(failed)")

            import soundfile as sf

            buf = io.BytesIO()
            sf.write(buf, result, sr, format="WAV")
            return {
                "status": "ok",
                "audio": base64.b64encode(buf.getvalue()).decode("ascii"),
                "sample_rate": sr,
                "applied": applied,
            }

        tasks = [_process_one(audio, sr) for audio, sr in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[dict] = []
        for r in results:
            if isinstance(r, Exception):
                output.append({"status": "error", "error": str(r)})
            else:
                output.append(r)
        return output

    async def batch_video_transform(
        self,
        files: list[np.ndarray],
        operation: str,
        params: dict,
    ) -> list[dict]:
        """Apply a single operation to each image file in parallel.

        Parameters
        ----------
        files : list of BGR numpy arrays
        operation : one of "color_grade", "smart_crop", "subtitle", "style", "super_resolution", "background_remove"
        params : dict of operation-specific parameters

        Returns
        -------
        list of result dicts with status and image (base64 PNG).
        """
        from app.services.transform.video_advanced import AdvancedVideoTransform
        from app.services.transform.video_transform import VideoTransformService

        video_svc = VideoTransformService()
        adv_video = AdvancedVideoTransform()

        async def _process_one(image: np.ndarray) -> dict:
            try:
                if operation == "color_grade":
                    result = await adv_video.color_grade(image, preset=params.get("preset", "cinematic"))
                elif operation == "smart_crop":
                    tw = params.get("target_width", 200)
                    th = params.get("target_height", 200)
                    method = params.get("method", "center_of_mass")
                    result = await adv_video.smart_crop(image, (tw, th), method=method)
                elif operation == "subtitle":
                    result = await adv_video.subtitle_burn(
                        image,
                        text=params.get("text", ""),
                        position=params.get("position", "bottom"),
                        font_scale=params.get("font_scale", 1.0),
                    )
                elif operation == "style":
                    result = video_svc.style_transfer(image, style=params.get("style", "sketch"))
                elif operation == "super_resolution":
                    result = video_svc.super_resolution(image, scale=params.get("scale", 2))
                elif operation == "background_remove":
                    result = video_svc.remove_background(image, method=params.get("method", "threshold"))
                else:
                    return {"status": "error", "error": f"Unknown operation: {operation}"}

                _, buf = cv2.imencode(".png", result)
                b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                return {"status": "ok", "image": b64}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        tasks = [_process_one(img) for img in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[dict] = []
        for r in results:
            if isinstance(r, Exception):
                output.append({"status": "error", "error": str(r)})
            else:
                output.append(r)
        return output
