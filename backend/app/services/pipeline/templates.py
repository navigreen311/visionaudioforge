"""Pre-built pipeline templates for common workflows."""

from __future__ import annotations

from typing import Any

from app.services.pipeline.nodes import NODE_REGISTRY, get_node


def _ports(node_type: str) -> tuple[dict, dict]:
    """Return (input_schema, output_schema) for a node type."""
    if node_type in NODE_REGISTRY:
        node = get_node(node_type)
        return node.input_schema, node.output_schema
    return {}, {}


def _build_definition(node_specs: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    """Build a pipeline definition from a list of (id, type, params) tuples.

    Every required input is wired to the nearest earlier node that publishes a
    port of that name. Edges used to be hard-coded to "output" -> "input" and
    one per adjacent pair, which was wrong twice over: nodes name their real
    ports (NormalizeNode takes `image` and returns `image`), and a node can
    need more than one of them. The audio nodes each need `sr`, which only
    `input_audio` produces — under the old scheme every template validated as
    missing required params, and at runtime the value arrived on a port the
    node never read.
    """
    nodes = [{"id": nid, "type": ntype, "params": params} for nid, ntype, params in node_specs]
    edges: list[dict[str, Any]] = []

    for index, (node_id, node_type, params) in enumerate(node_specs):
        inputs, _ = _ports(node_type)
        for port, spec in inputs.items():
            if not spec.get("required") or port in params:
                continue

            # Nearest earlier producer of this port wins.
            source = next(
                (
                    node_specs[j]
                    for j in range(index - 1, -1, -1)
                    if port in _ports(node_specs[j][1])[1]
                ),
                None,
            )
            if source is None and index > 0:
                # Nothing publishes this name; fall back to the immediate
                # predecessor's first output so the chain still connects.
                previous = node_specs[index - 1]
                previous_outputs = list(_ports(previous[1])[1])
                if previous_outputs:
                    edges.append({
                        "from": previous[0],
                        "to": node_id,
                        "from_port": previous_outputs[0],
                        "to_port": port,
                    })
                continue

            if source is not None:
                edges.append({
                    "from": source[0],
                    "to": node_id,
                    "from_port": port,
                    "to_port": port,
                })

    return {"nodes": nodes, "edges": edges}


PIPELINE_TEMPLATES: dict[str, dict[str, Any]] = {
    "image-preprocessing": {
        "name": "Image Preprocessing",
        "description": "Standard image preprocessing: normalize, convert color space, and resize.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("normalize_1", "normalize", {"method": "min_max"}),
            ("color_1", "color_convert", {"target": "rgb"}),
            ("resize_1", "resize", {"width": 224, "height": 224}),
            ("output_1", "save_asset", {"filename": "preprocessed.npy", "format": "npy"}),
        ]),
    },
    "object-detection": {
        "name": "Object Detection",
        "description": "Detect objects in images with optional alert when objects are found.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("normalize_1", "normalize", {"method": "min_max"}),
            ("detect_1", "detect_objects", {"confidence": 0.5}),
            ("alert_1", "alert", {"message": "Objects detected", "severity": "info"}),
            ("output_1", "save_asset", {"filename": "detections.json", "format": "json"}),
        ]),
    },
    "audio-analysis": {
        "name": "Audio Analysis",
        "description": "Full audio analysis pipeline: STFT, mel spectrogram, and MFCC extraction.",
        "category": "Audio",
        "definition": _build_definition([
            ("input_1", "input_audio", {"path": ""}),
            ("stft_1", "stft", {"n_fft": 2048}),
            ("mel_1", "mel_spectrogram", {"n_mels": 128}),
            ("mfcc_1", "mfcc", {"n_mfcc": 13}),
            ("output_1", "save_asset", {"filename": "audio_features.npy", "format": "npy"}),
        ]),
    },
    "motion-detection": {
        "name": "Motion Detection",
        "description": "Detect motion via frame differencing with threshold filtering and alert.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("diff_1", "frame_diff", {}),
            ("filter_1", "filter", {"condition": "threshold", "value": 0.1}),
            ("alert_1", "alert", {"message": "Motion detected", "severity": "warning"}),
            ("output_1", "save_asset", {"filename": "motion.json", "format": "json"}),
        ]),
    },
    "cross-modal-search": {
        "name": "Cross-Modal Search",
        "description": "Embed images with CLIP and search a FAISS index for similar items.",
        "category": "Search",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("clip_1", "embed_clip", {}),
            ("search_1", "faiss_search", {"index_path": "", "top_k": 10}),
            ("output_1", "save_asset", {"filename": "search_results.json", "format": "json"}),
        ]),
    },
    "audio-augmentation": {
        "name": "Audio Augmentation",
        "description": "Apply audio augmentations such as noise injection, pitch shift, or time stretch.",
        "category": "Audio",
        "definition": _build_definition([
            ("input_1", "input_audio", {"path": ""}),
            ("augment_1", "augment_audio", {"augmentation": "noise", "intensity": 0.005}),
            ("output_1", "save_asset", {"filename": "augmented.npy", "format": "npy"}),
        ]),
    },
    "video-surveillance": {
        "name": "Video Surveillance",
        "description": "Detect objects and compute optical flow for video surveillance with alerting.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("detect_1", "detect_objects", {"confidence": 0.5}),
            ("flow_1", "optical_flow", {}),
            ("alert_1", "alert", {"message": "Surveillance event", "severity": "warning"}),
            ("output_1", "save_asset", {"filename": "surveillance.json", "format": "json"}),
        ]),
    },
    "speech-pipeline": {
        "name": "Speech Pipeline",
        "description": "Extract speech features via STFT and MFCC for speech recognition tasks.",
        "category": "Audio",
        "definition": _build_definition([
            ("input_1", "input_audio", {"path": ""}),
            ("stft_1", "stft", {"n_fft": 2048}),
            ("mfcc_1", "mfcc", {"n_mfcc": 13}),
            ("output_1", "save_asset", {"filename": "speech_features.npy", "format": "npy"}),
        ]),
    },
    "image-transform": {
        "name": "Image Transform",
        "description": "Normalize an image and apply Canny edge detection.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("normalize_1", "normalize", {"method": "min_max"}),
            ("edge_1", "edge_detect", {"low_threshold": 50, "high_threshold": 150}),
            ("output_1", "save_asset", {"filename": "edges.png", "format": "png"}),
        ]),
    },
    "full-analysis": {
        "name": "Full Analysis",
        "description": "Complete image analysis: normalize, detect objects, embed with CLIP, and search FAISS.",
        "category": "Vision",
        "definition": _build_definition([
            ("input_1", "input_image", {"path": ""}),
            ("normalize_1", "normalize", {"method": "min_max"}),
            ("detect_1", "detect_objects", {"confidence": 0.5}),
            ("clip_1", "embed_clip", {}),
            ("search_1", "faiss_search", {"index_path": "", "top_k": 5}),
            ("output_1", "save_asset", {"filename": "full_analysis.json", "format": "json"}),
        ]),
    },
}


def get_template(name: str) -> dict[str, Any] | None:
    """Return a template by name, or None if not found."""
    return PIPELINE_TEMPLATES.get(name)


def list_templates() -> list[dict[str, Any]]:
    """Return all templates as a list with their keys."""
    result = []
    for key, tmpl in PIPELINE_TEMPLATES.items():
        result.append({"key": key, **tmpl})
    return result
