"""Pipeline node definitions — 26 node types across 7 categories."""

from __future__ import annotations

import abc
from typing import Any


class BaseNode(abc.ABC):
    """Abstract base for all pipeline nodes."""

    name: str = ""
    category: str = ""
    description: str = ""

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return JSON-serialisable dict describing accepted inputs."""
        return {}

    @property
    def output_schema(self) -> dict[str, Any]:
        """Return JSON-serialisable dict describing produced outputs."""
        return {}

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the node. Subclasses must override."""
        try:
            return await self._run(inputs)
        except Exception as exc:
            return {"error": str(exc)}

    @abc.abstractmethod
    async def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# INPUT nodes
# ---------------------------------------------------------------------------

class InputImageNode(BaseNode):
    name = "Input Image"
    category = "Input"
    description = "Load an image from a file path or upload."

    @property
    def input_schema(self) -> dict:
        return {"path": {"type": "string", "description": "Image file path", "required": True}}

    @property
    def output_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Loaded image array"}}

    async def _run(self, inputs: dict) -> dict:
        import numpy as np
        from PIL import Image

        path = inputs.get("path") or inputs.get("image")
        if not path:
            return {"error": "No image path provided"}
        img = Image.open(path).convert("RGB")
        return {"image": np.array(img)}


class InputAudioNode(BaseNode):
    name = "Input Audio"
    category = "Input"
    description = "Load an audio file."

    @property
    def input_schema(self) -> dict:
        return {"path": {"type": "string", "description": "Audio file path", "required": True}}

    @property
    def output_schema(self) -> dict:
        return {
            "audio": {"type": "ndarray", "description": "Audio waveform"},
            "sr": {"type": "integer", "description": "Sample rate"},
        }

    async def _run(self, inputs: dict) -> dict:
        import librosa

        path = inputs["path"]
        y, sr = librosa.load(path, sr=None)
        return {"audio": y, "sr": int(sr)}


class InputVideoNode(BaseNode):
    name = "Input Video"
    category = "Input"
    description = "Load video frames from a file."

    @property
    def input_schema(self) -> dict:
        return {
            "path": {"type": "string", "description": "Video file path", "required": True},
            "max_frames": {"type": "integer", "description": "Max frames to extract", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"frames": {"type": "list[ndarray]", "description": "Extracted video frames"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2

        path = inputs["path"]
        max_frames = inputs.get("max_frames", 30)
        cap = cv2.VideoCapture(path)
        frames = []
        while len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()
        return {"frames": frames}


# ---------------------------------------------------------------------------
# VISION nodes
# ---------------------------------------------------------------------------

class NormalizeNode(BaseNode):
    name = "Normalize"
    category = "Vision"
    description = "Normalize image using min-max or z-score."

    @property
    def input_schema(self) -> dict:
        return {
            "image": {"type": "ndarray", "description": "Input image", "required": True},
            "method": {"type": "string", "enum": ["min_max", "z_score"], "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Normalized image"}}

    async def _run(self, inputs: dict) -> dict:
        import numpy as np

        img = np.asarray(inputs["image"], dtype=np.float32)
        method = inputs.get("method", "min_max")
        if method == "z_score":
            mean, std = img.mean(), img.std()
            img = (img - mean) / (std + 1e-8)
        else:
            mn, mx = img.min(), img.max()
            img = (img - mn) / (mx - mn + 1e-8)
        return {"image": img}


class ColorConvertNode(BaseNode):
    name = "Color Convert"
    category = "Vision"
    description = "Convert image color space (rgb/hsv/gray)."

    @property
    def input_schema(self) -> dict:
        return {
            "image": {"type": "ndarray", "description": "Input image", "required": True},
            "target": {"type": "string", "enum": ["rgb", "hsv", "gray"], "required": True},
        }

    @property
    def output_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Converted image"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2
        import numpy as np

        img = np.asarray(inputs["image"], dtype=np.uint8)
        target = inputs.get("target", "gray")
        conversions = {
            "gray": cv2.COLOR_RGB2GRAY,
            "hsv": cv2.COLOR_RGB2HSV,
            "rgb": cv2.COLOR_BGR2RGB,
        }
        code = conversions.get(target)
        if code is None:
            return {"error": f"Unknown target color space: {target}"}
        return {"image": cv2.cvtColor(img, code)}


class DetectObjectsNode(BaseNode):
    name = "Detect Objects"
    category = "Vision"
    description = "Run YOLO object detection on an image."

    @property
    def input_schema(self) -> dict:
        return {
            "image": {"type": "ndarray", "description": "Input image", "required": True},
            "confidence": {"type": "number", "description": "Confidence threshold", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"detections": {"type": "list[dict]", "description": "Detected objects with bbox and label"}}

    async def _run(self, inputs: dict) -> dict:
        # Stub — real impl would load a YOLO model
        return {"detections": []}


class OpticalFlowNode(BaseNode):
    name = "Optical Flow"
    category = "Vision"
    description = "Compute optical flow using Lucas-Kanade or Farneback."

    @property
    def input_schema(self) -> dict:
        return {
            "frames": {"type": "list[ndarray]", "description": "Two or more video frames", "required": True},
            "method": {"type": "string", "enum": ["lk", "farneback"], "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"flow": {"type": "ndarray", "description": "Optical flow field"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2
        import numpy as np

        frames = inputs["frames"]
        if len(frames) < 2:
            return {"error": "Need at least 2 frames"}
        prev_gray = cv2.cvtColor(np.asarray(frames[0], dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        curr_gray = cv2.cvtColor(np.asarray(frames[1], dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        method = inputs.get("method", "farneback")
        if method == "farneback":
            flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        else:
            # Lucas-Kanade sparse
            pts = cv2.goodFeaturesToTrack(prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7)
            if pts is None:
                return {"flow": np.zeros((0, 2))}
            new_pts, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, pts, None)
            flow = (new_pts - pts)[st.flatten() == 1]
        return {"flow": flow}


class FrameDiffNode(BaseNode):
    name = "Frame Difference"
    category = "Vision"
    description = "Compute frame differencing for motion detection."

    @property
    def input_schema(self) -> dict:
        return {"frames": {"type": "list[ndarray]", "description": "Two or more frames", "required": True}}

    @property
    def output_schema(self) -> dict:
        return {"diff": {"type": "ndarray", "description": "Difference image"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2
        import numpy as np

        frames = inputs["frames"]
        if len(frames) < 2:
            return {"error": "Need at least 2 frames"}
        a = cv2.cvtColor(np.asarray(frames[0], dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        b = cv2.cvtColor(np.asarray(frames[1], dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        return {"diff": cv2.absdiff(a, b)}


class EdgeDetectNode(BaseNode):
    name = "Edge Detect"
    category = "Vision"
    description = "Detect edges using Canny."

    @property
    def input_schema(self) -> dict:
        return {
            "image": {"type": "ndarray", "description": "Input image", "required": True},
            "low_threshold": {"type": "integer", "description": "Canny low threshold", "required": False},
            "high_threshold": {"type": "integer", "description": "Canny high threshold", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Edge image"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2
        import numpy as np

        img = np.asarray(inputs["image"], dtype=np.uint8)
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        low = inputs.get("low_threshold", 50)
        high = inputs.get("high_threshold", 150)
        return {"image": cv2.Canny(img, low, high)}


# ---------------------------------------------------------------------------
# AUDIO nodes
# ---------------------------------------------------------------------------

class STFTNode(BaseNode):
    name = "STFT"
    category = "Audio"
    description = "Compute Short-Time Fourier Transform."

    @property
    def input_schema(self) -> dict:
        return {
            "audio": {"type": "ndarray", "description": "Audio waveform", "required": True},
            "sr": {"type": "integer", "description": "Sample rate", "required": True},
            "n_fft": {"type": "integer", "description": "FFT window size", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"spectrogram": {"type": "ndarray", "description": "STFT magnitude spectrogram"}}

    async def _run(self, inputs: dict) -> dict:
        import librosa
        import numpy as np

        y = np.asarray(inputs["audio"], dtype=np.float32)
        n_fft = inputs.get("n_fft", 2048)
        S = np.abs(librosa.stft(y, n_fft=n_fft))
        return {"spectrogram": S}


class MelSpectrogramNode(BaseNode):
    name = "Mel Spectrogram"
    category = "Audio"
    description = "Compute Mel spectrogram."

    @property
    def input_schema(self) -> dict:
        return {
            "audio": {"type": "ndarray", "description": "Audio waveform", "required": True},
            "sr": {"type": "integer", "description": "Sample rate", "required": True},
            "n_mels": {"type": "integer", "description": "Number of mel bands", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"mel_spectrogram": {"type": "ndarray", "description": "Mel spectrogram"}}

    async def _run(self, inputs: dict) -> dict:
        import librosa
        import numpy as np

        y = np.asarray(inputs["audio"], dtype=np.float32)
        sr = inputs["sr"]
        n_mels = inputs.get("n_mels", 128)
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels)
        return {"mel_spectrogram": S}


class MFCCNode(BaseNode):
    name = "MFCC"
    category = "Audio"
    description = "Extract MFCCs from audio."

    @property
    def input_schema(self) -> dict:
        return {
            "audio": {"type": "ndarray", "description": "Audio waveform", "required": True},
            "sr": {"type": "integer", "description": "Sample rate", "required": True},
            "n_mfcc": {"type": "integer", "description": "Number of MFCCs", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"mfcc": {"type": "ndarray", "description": "MFCC feature matrix"}}

    async def _run(self, inputs: dict) -> dict:
        import librosa
        import numpy as np

        y = np.asarray(inputs["audio"], dtype=np.float32)
        sr = inputs["sr"]
        n_mfcc = inputs.get("n_mfcc", 13)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return {"mfcc": mfcc}


class AugmentAudioNode(BaseNode):
    name = "Augment Audio"
    category = "Audio"
    description = "Apply audio augmentations (noise, pitch-shift, time-stretch)."

    @property
    def input_schema(self) -> dict:
        return {
            "audio": {"type": "ndarray", "description": "Audio waveform", "required": True},
            "sr": {"type": "integer", "description": "Sample rate", "required": True},
            "augmentation": {"type": "string", "enum": ["noise", "pitch_shift", "time_stretch"], "required": True},
            "intensity": {"type": "number", "description": "Augmentation intensity", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"audio": {"type": "ndarray", "description": "Augmented audio"}, "sr": {"type": "integer"}}

    async def _run(self, inputs: dict) -> dict:
        import librosa
        import numpy as np

        y = np.asarray(inputs["audio"], dtype=np.float32)
        sr = inputs["sr"]
        aug = inputs.get("augmentation", "noise")
        intensity = inputs.get("intensity", 0.005)
        if aug == "noise":
            y = y + intensity * np.random.randn(len(y)).astype(np.float32)
        elif aug == "pitch_shift":
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=intensity)
        elif aug == "time_stretch":
            rate = 1.0 + intensity
            y = librosa.effects.time_stretch(y, rate=rate)
        return {"audio": y, "sr": sr}


# ---------------------------------------------------------------------------
# SEARCH nodes
# ---------------------------------------------------------------------------

class EmbedCLIPNode(BaseNode):
    name = "Embed CLIP"
    category = "Search"
    description = "Generate CLIP embedding for an image."

    @property
    def input_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Input image", "required": True}}

    @property
    def output_schema(self) -> dict:
        return {"embedding": {"type": "ndarray", "description": "CLIP embedding vector"}}

    async def _run(self, inputs: dict) -> dict:
        import numpy as np

        # Stub — real impl would use transformers CLIP model
        img = np.asarray(inputs["image"])
        embedding = np.random.randn(512).astype(np.float32)
        return {"embedding": embedding}


class FAISSSearchNode(BaseNode):
    name = "FAISS Search"
    category = "Search"
    description = "Search a FAISS index with an embedding vector."

    @property
    def input_schema(self) -> dict:
        return {
            "embedding": {"type": "ndarray", "description": "Query embedding", "required": True},
            "index_path": {"type": "string", "description": "Path to FAISS index", "required": True},
            "top_k": {"type": "integer", "description": "Number of results", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {
            "distances": {"type": "list[float]", "description": "Distance scores"},
            "indices": {"type": "list[int]", "description": "Matched indices"},
        }

    async def _run(self, inputs: dict) -> dict:
        import faiss
        import numpy as np

        embedding = np.asarray(inputs["embedding"], dtype=np.float32).reshape(1, -1)
        index = faiss.read_index(inputs["index_path"])
        top_k = inputs.get("top_k", 5)
        distances, indices = index.search(embedding, top_k)
        return {
            "distances": distances[0].tolist(),
            "indices": indices[0].tolist(),
        }


# ---------------------------------------------------------------------------
# ACTION nodes
# ---------------------------------------------------------------------------

class AlertNode(BaseNode):
    name = "Alert"
    category = "Action"
    description = "Create an alert/notification."

    @property
    def input_schema(self) -> dict:
        return {
            "message": {"type": "string", "description": "Alert message", "required": True},
            "severity": {"type": "string", "enum": ["info", "warning", "critical"], "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"alert_id": {"type": "string", "description": "Created alert ID"}}

    async def _run(self, inputs: dict) -> dict:
        import uuid

        alert_id = str(uuid.uuid4())
        # In production this would persist to DB / send notification
        return {"alert_id": alert_id, "message": inputs["message"], "severity": inputs.get("severity", "info")}


class WebhookNode(BaseNode):
    name = "Webhook"
    category = "Action"
    description = "POST data to a webhook URL."

    @property
    def input_schema(self) -> dict:
        return {
            "url": {"type": "string", "description": "Webhook URL", "required": True},
            "payload": {"type": "object", "description": "JSON payload to send", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"status_code": {"type": "integer"}, "response": {"type": "string"}}

    async def _run(self, inputs: dict) -> dict:
        import httpx

        url = inputs["url"]
        payload = inputs.get("payload", {})
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        return {"status_code": resp.status_code, "response": resp.text[:500]}


class SaveAssetNode(BaseNode):
    name = "Save Asset"
    category = "Action"
    description = "Save output to storage."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Data to save", "required": True},
            "filename": {"type": "string", "description": "Output filename", "required": True},
            "format": {"type": "string", "enum": ["npy", "png", "json"], "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"path": {"type": "string", "description": "Saved file path"}}

    async def _run(self, inputs: dict) -> dict:
        import json
        import os

        import numpy as np

        data = inputs["data"]
        filename = inputs["filename"]
        fmt = inputs.get("format", "npy")
        out_dir = "/tmp/pipeline_assets"
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, filename)
        if fmt == "npy":
            np.save(path, np.asarray(data))
            path += ".npy"
        elif fmt == "json":
            with open(path, "w") as f:
                json.dump(data if isinstance(data, (dict, list)) else str(data), f)
        elif fmt == "png":
            from PIL import Image

            Image.fromarray(np.asarray(data, dtype=np.uint8)).save(path)
        return {"path": path}


# ---------------------------------------------------------------------------
# CONTROL FLOW nodes
# ---------------------------------------------------------------------------

class ConditionalNode(BaseNode):
    name = "Conditional"
    category = "Control"
    description = "Route data based on a condition: pass to output_true or output_false."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Input data to evaluate", "required": True},
            "condition": {"type": "string", "description": "Condition key to check in data", "required": True},
        }

    @property
    def output_schema(self) -> dict:
        return {
            "output_true": {"type": "any", "description": "Data if condition is true"},
            "output_false": {"type": "any", "description": "Data if condition is false"},
            "branch": {"type": "string", "description": "'true' or 'false'"},
        }

    async def _run(self, inputs: dict) -> dict:
        data = inputs.get("data", {})
        condition_key = inputs.get("condition", "")
        # Evaluate: check if key exists and is truthy in data
        if isinstance(data, dict):
            result = bool(data.get(condition_key))
        else:
            result = bool(data)
        branch = "true" if result else "false"
        return {
            "output_true": data if result else None,
            "output_false": data if not result else None,
            "branch": branch,
        }


class LoopNode(BaseNode):
    name = "Loop"
    category = "Control"
    description = "Repeat processing N times or until a condition is met."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Input data to iterate over", "required": True},
            "iterations": {"type": "integer", "description": "Number of iterations", "required": False},
            "until_key": {"type": "string", "description": "Stop when this key is truthy", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {
            "output": {"type": "any", "description": "Final data after looping"},
            "iteration_count": {"type": "integer", "description": "How many iterations ran"},
        }

    async def _run(self, inputs: dict) -> dict:
        data = inputs.get("data")
        iterations = inputs.get("iterations", 1)
        until_key = inputs.get("until_key")
        count = 0
        for _ in range(iterations):
            count += 1
            if until_key and isinstance(data, dict) and data.get(until_key):
                break
        return {"output": data, "iteration_count": count}


class DelayNode(BaseNode):
    name = "Delay"
    category = "Control"
    description = "Wait N seconds before passing data through (for rate limiting)."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Pass-through data", "required": False},
            "seconds": {"type": "number", "description": "Seconds to wait", "required": True},
        }

    @property
    def output_schema(self) -> dict:
        return {"data": {"type": "any", "description": "Pass-through data unchanged"}}

    async def _run(self, inputs: dict) -> dict:
        import asyncio

        seconds = min(inputs.get("seconds", 1), 30)  # Cap at 30s safety
        await asyncio.sleep(seconds)
        return {"data": inputs.get("data")}


class LogNode(BaseNode):
    name = "Log"
    category = "Control"
    description = "Log input data to structured logger and pass through."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Data to log", "required": True},
            "label": {"type": "string", "description": "Log label/tag", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"data": {"type": "any", "description": "Pass-through data unchanged"}}

    async def _run(self, inputs: dict) -> dict:
        import logging

        logger = logging.getLogger("pipeline.log_node")
        label = inputs.get("label", "LogNode")
        data = inputs.get("data")
        # Log a summary — avoid dumping huge arrays
        summary = str(data)[:500] if data is not None else "None"
        logger.info("[%s] %s", label, summary)
        return {"data": data}


class HTTPRequestNode(BaseNode):
    name = "HTTP Request"
    category = "Control"
    description = "Make an HTTP request to an external URL and return the response."

    @property
    def input_schema(self) -> dict:
        return {
            "url": {"type": "string", "description": "Target URL", "required": True},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "required": False},
            "body": {"type": "object", "description": "JSON body for POST/PUT", "required": False},
            "headers": {"type": "object", "description": "Request headers", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {
            "status_code": {"type": "integer", "description": "HTTP status code"},
            "response": {"type": "string", "description": "Response body (truncated)"},
        }

    async def _run(self, inputs: dict) -> dict:
        import httpx

        url = inputs["url"]
        method = inputs.get("method", "GET").upper()
        body = inputs.get("body")
        headers = inputs.get("headers", {})
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, json=body, headers=headers)
            elif method == "PUT":
                resp = await client.put(url, json=body, headers=headers)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
        return {"status_code": resp.status_code, "response": resp.text[:1000]}


# ---------------------------------------------------------------------------
# TRANSFORM nodes
# ---------------------------------------------------------------------------

class ResizeNode(BaseNode):
    name = "Resize"
    category = "Transform"
    description = "Resize an image to target dimensions."

    @property
    def input_schema(self) -> dict:
        return {
            "image": {"type": "ndarray", "description": "Input image", "required": True},
            "width": {"type": "integer", "description": "Target width", "required": True},
            "height": {"type": "integer", "description": "Target height", "required": True},
        }

    @property
    def output_schema(self) -> dict:
        return {"image": {"type": "ndarray", "description": "Resized image"}}

    async def _run(self, inputs: dict) -> dict:
        import cv2
        import numpy as np

        img = np.asarray(inputs["image"], dtype=np.uint8)
        w = inputs.get("width", 224)
        h = inputs.get("height", 224)
        return {"image": cv2.resize(img, (w, h))}


class FilterNode(BaseNode):
    name = "Filter"
    category = "Transform"
    description = "Filter data by threshold or condition."

    @property
    def input_schema(self) -> dict:
        return {
            "data": {"type": "any", "description": "Input data (list or array)", "required": True},
            "condition": {"type": "string", "enum": ["threshold", "nonzero", "top_k"], "required": True},
            "value": {"type": "number", "description": "Threshold/k value", "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"data": {"type": "any", "description": "Filtered data"}}

    async def _run(self, inputs: dict) -> dict:
        import numpy as np

        data = np.asarray(inputs["data"])
        condition = inputs.get("condition", "threshold")
        value = inputs.get("value", 0.5)
        if condition == "threshold":
            return {"data": data[data >= value]}
        elif condition == "nonzero":
            return {"data": data[data != 0]}
        elif condition == "top_k":
            k = int(value)
            indices = np.argsort(data.flatten())[-k:]
            return {"data": data.flatten()[indices]}
        return {"data": data}


class MergeNode(BaseNode):
    name = "Merge"
    category = "Transform"
    description = "Combine multiple inputs into a single output."

    @property
    def input_schema(self) -> dict:
        return {
            "inputs": {"type": "list[any]", "description": "List of inputs to merge", "required": True},
            "strategy": {"type": "string", "enum": ["concat", "stack", "dict"], "required": False},
        }

    @property
    def output_schema(self) -> dict:
        return {"merged": {"type": "any", "description": "Merged output"}}

    async def _run(self, inputs: dict) -> dict:
        import numpy as np

        items = inputs.get("inputs", [])
        strategy = inputs.get("strategy", "dict")
        if strategy == "concat":
            return {"merged": np.concatenate([np.asarray(i) for i in items])}
        elif strategy == "stack":
            return {"merged": np.stack([np.asarray(i) for i in items])}
        else:
            return {"merged": {f"input_{i}": v for i, v in enumerate(items)}}


# ---------------------------------------------------------------------------
# Node Registry
# ---------------------------------------------------------------------------

NODE_REGISTRY: dict[str, type[BaseNode]] = {
    "input_image": InputImageNode,
    "input_audio": InputAudioNode,
    "input_video": InputVideoNode,
    "normalize": NormalizeNode,
    "color_convert": ColorConvertNode,
    "detect_objects": DetectObjectsNode,
    "optical_flow": OpticalFlowNode,
    "frame_diff": FrameDiffNode,
    "edge_detect": EdgeDetectNode,
    "stft": STFTNode,
    "mel_spectrogram": MelSpectrogramNode,
    "mfcc": MFCCNode,
    "augment_audio": AugmentAudioNode,
    "embed_clip": EmbedCLIPNode,
    "faiss_search": FAISSSearchNode,
    "alert": AlertNode,
    "webhook": WebhookNode,
    "save_asset": SaveAssetNode,
    "resize": ResizeNode,
    "filter": FilterNode,
    "merge": MergeNode,
    "conditional": ConditionalNode,
    "loop": LoopNode,
    "delay": DelayNode,
    "log": LogNode,
    "http_request": HTTPRequestNode,
}


def get_node(node_type: str) -> BaseNode:
    """Instantiate and return a node by type string."""
    cls = NODE_REGISTRY.get(node_type)
    if cls is None:
        raise KeyError(f"Unknown node type: {node_type}")
    return cls()
