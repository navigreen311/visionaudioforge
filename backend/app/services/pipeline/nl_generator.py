"""Natural language to pipeline generator — converts descriptions to pipeline definitions."""

from __future__ import annotations

import re
import uuid
from typing import Any


# Mapping from keywords to node type sequences
_PATTERN_MAP: list[tuple[list[str], list[dict[str, Any]]]] = [
    # "detect objects in images"
    (
        ["detect", "object", "image"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "detect_objects", "params": {}},
            {"type": "save_asset", "params": {"filename": "output.json", "format": "json"}},
        ],
    ),
    # "analyze audio for speech"
    (
        ["audio", "speech"],
        [
            {"type": "input_audio", "params": {"path": ""}},
            {"type": "stft", "params": {}},
            {"type": "mfcc", "params": {}},
            {"type": "save_asset", "params": {"filename": "output.npy", "format": "npy"}},
        ],
    ),
    # "analyze audio" (general)
    (
        ["analyze", "audio"],
        [
            {"type": "input_audio", "params": {"path": ""}},
            {"type": "stft", "params": {}},
            {"type": "mfcc", "params": {}},
            {"type": "save_asset", "params": {"filename": "output.npy", "format": "npy"}},
        ],
    ),
    # "find similar images"
    (
        ["similar", "image"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "embed_clip", "params": {}},
            {"type": "faiss_search", "params": {"index_path": "", "top_k": 5}},
        ],
    ),
    # "preprocess and normalize images"
    (
        ["preprocess", "normalize"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "normalize", "params": {}},
            {"type": "color_convert", "params": {"target": "rgb"}},
            {"type": "save_asset", "params": {"filename": "output.npy", "format": "npy"}},
        ],
    ),
    # "create alert when motion detected"
    (
        ["motion", "alert"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "frame_diff", "params": {}},
            {"type": "filter", "params": {"condition": "threshold", "value": 0.1}},
            {"type": "alert", "params": {"message": "Motion detected", "severity": "warning"}},
        ],
    ),
    # "motion detection" (without alert keyword)
    (
        ["motion", "detect"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "frame_diff", "params": {}},
            {"type": "filter", "params": {"condition": "threshold", "value": 0.1}},
            {"type": "alert", "params": {"message": "Motion detected", "severity": "warning"}},
        ],
    ),
    # "edge detection"
    (
        ["edge", "detect"],
        [
            {"type": "input_image", "params": {"path": ""}},
            {"type": "normalize", "params": {}},
            {"type": "edge_detect", "params": {}},
            {"type": "save_asset", "params": {"filename": "edges.png", "format": "png"}},
        ],
    ),
    # "optical flow"
    (
        ["optical", "flow"],
        [
            {"type": "input_video", "params": {"path": ""}},
            {"type": "optical_flow", "params": {}},
            {"type": "save_asset", "params": {"filename": "flow.npy", "format": "npy"}},
        ],
    ),
    # "augment audio"
    (
        ["augment", "audio"],
        [
            {"type": "input_audio", "params": {"path": ""}},
            {"type": "augment_audio", "params": {"augmentation": "noise"}},
            {"type": "save_asset", "params": {"filename": "augmented.npy", "format": "npy"}},
        ],
    ),
]

# Output type mapping for next-node suggestions
_OUTPUT_TYPE_MAP: dict[str, str] = {
    "input_image": "image",
    "input_audio": "audio",
    "input_video": "frames",
    "normalize": "image",
    "color_convert": "image",
    "detect_objects": "detections",
    "optical_flow": "flow",
    "frame_diff": "diff",
    "edge_detect": "image",
    "stft": "spectrogram",
    "mel_spectrogram": "mel_spectrogram",
    "mfcc": "mfcc",
    "augment_audio": "audio",
    "embed_clip": "embedding",
    "faiss_search": "results",
    "alert": "alert_id",
    "webhook": "response",
    "save_asset": "path",
    "resize": "image",
    "filter": "data",
    "merge": "merged",
    "conditional": "output",
    "loop": "output",
    "delay": "data",
    "log": "data",
    "http_request": "response",
}

# What can follow each output type
_NEXT_SUGGESTIONS: dict[str, list[str]] = {
    "image": ["normalize", "color_convert", "resize", "edge_detect", "detect_objects", "embed_clip", "save_asset", "filter"],
    "audio": ["stft", "mel_spectrogram", "mfcc", "augment_audio", "save_asset"],
    "frames": ["optical_flow", "frame_diff"],
    "spectrogram": ["mel_spectrogram", "save_asset", "filter"],
    "mel_spectrogram": ["mfcc", "save_asset"],
    "mfcc": ["save_asset"],
    "detections": ["alert", "webhook", "save_asset", "filter", "log"],
    "embedding": ["faiss_search", "save_asset"],
    "results": ["save_asset", "alert", "webhook", "log"],
    "diff": ["filter", "alert", "save_asset"],
    "flow": ["save_asset", "filter"],
    "data": ["save_asset", "alert", "webhook", "log"],
    "merged": ["save_asset", "log"],
}


class NLPipelineGenerator:
    """Generate pipeline definitions from natural language descriptions."""

    async def generate_from_description(self, description: str) -> dict[str, Any]:
        """Parse a natural language description and produce a pipeline definition.

        Uses keyword matching against known patterns to select the best
        sequence of nodes, then auto-generates edges connecting them
        sequentially.

        Returns a valid pipeline definition ``{"nodes": [...], "edges": [...]}``.
        """
        desc_lower = description.lower()
        tokens = set(re.findall(r"[a-z]+", desc_lower))

        best_match: list[dict[str, Any]] | None = None
        best_score = 0

        for keywords, node_templates in _PATTERN_MAP:
            score = sum(1 for kw in keywords if kw in tokens)
            # Require at least 2 keyword matches or all keywords matched
            if score >= min(2, len(keywords)) and score > best_score:
                best_score = score
                best_match = node_templates

        if best_match is None:
            # Fallback: create a simple input → output pipeline based on keywords
            if any(kw in tokens for kw in ("audio", "sound", "music", "speech")):
                best_match = [
                    {"type": "input_audio", "params": {"path": ""}},
                    {"type": "save_asset", "params": {"filename": "output.npy", "format": "npy"}},
                ]
            else:
                best_match = [
                    {"type": "input_image", "params": {"path": ""}},
                    {"type": "save_asset", "params": {"filename": "output.npy", "format": "npy"}},
                ]

        # Build nodes with unique IDs
        nodes = []
        for i, template in enumerate(best_match):
            node_id = f"node_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "id": node_id,
                "type": template["type"],
                "params": dict(template["params"]),
            })

        # Build edges connecting nodes sequentially
        edges = []
        for i in range(len(nodes) - 1):
            edges.append({
                "from": nodes[i]["id"],
                "to": nodes[i + 1]["id"],
                "from_port": "output",
                "to_port": "input",
            })

        return {"nodes": nodes, "edges": edges}

    async def suggest_next_nodes(self, current_nodes: list[str]) -> list[str]:
        """Given a list of current node types, suggest logical next nodes.

        Looks at the last node's output type and returns node types that
        accept that output type.
        """
        if not current_nodes:
            return ["input_image", "input_audio", "input_video"]

        last_node = current_nodes[-1]
        output_type = _OUTPUT_TYPE_MAP.get(last_node)

        if output_type is None:
            # Unknown node, suggest generic actions
            return ["save_asset", "alert", "webhook", "log"]

        suggestions = _NEXT_SUGGESTIONS.get(output_type, ["save_asset", "log"])

        # Filter out nodes already in the pipeline (except save_asset)
        existing = set(current_nodes)
        filtered = [s for s in suggestions if s not in existing or s == "save_asset"]

        return filtered if filtered else ["save_asset", "log"]
