"""Scene graph extraction — spatial relationships from detections and temporal edges from video."""

from __future__ import annotations

import math
from typing import Any


def _bbox_center(bbox: dict) -> tuple[float, float]:
    """Return (cx, cy) of a bbox dict with keys x, y, w, h."""
    return bbox["x"] + bbox["w"] / 2, bbox["y"] + bbox["h"] / 2


def _bbox_distance(a: dict, b: dict) -> float:
    """Euclidean distance between bbox centers."""
    cx_a, cy_a = _bbox_center(a)
    cx_b, cy_b = _bbox_center(b)
    return math.sqrt((cx_a - cx_b) ** 2 + (cy_a - cy_b) ** 2)


def _bbox_contains(outer: dict, inner: dict) -> bool:
    """Check if *outer* bbox fully contains *inner*."""
    return (
        inner["x"] >= outer["x"]
        and inner["y"] >= outer["y"]
        and inner["x"] + inner["w"] <= outer["x"] + outer["w"]
        and inner["y"] + inner["h"] <= outer["y"] + outer["h"]
    )


def _bbox_overlaps(a: dict, b: dict) -> bool:
    """Check if two bboxes overlap at all."""
    if a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]:
        return False
    if a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]:
        return False
    return True


class SceneGraphExtractor:
    """Builds scene graphs from object detections with spatial and temporal relationships."""

    @staticmethod
    def extract_scene_graph(
        image: Any,
        detections: list[dict],
    ) -> dict:
        """Extract a scene graph from a single image's detections.

        Each detection dict should have: class_name, bbox ({x,y,w,h}), confidence.
        Returns {"nodes": [...], "edges": [...]}.
        """
        nodes: list[dict] = []
        edges: list[dict] = []

        # Build nodes
        for idx, det in enumerate(detections):
            node = {
                "id": f"det_{idx}",
                "node_type": "object",
                "label": det.get("class_name", "unknown"),
                "properties": {
                    "bbox": det.get("bbox", {}),
                    "confidence": det.get("confidence", 0.0),
                    "detection_index": idx,
                },
            }
            nodes.append(node)

        # Compute spatial relationships
        for i in range(len(detections)):
            for j in range(i + 1, len(detections)):
                bbox_i = detections[i].get("bbox", {})
                bbox_j = detections[j].get("bbox", {})
                if not bbox_i or not bbox_j:
                    continue

                rel_edges = SceneGraphExtractor._spatial_relations(
                    nodes[i]["id"], bbox_i, nodes[j]["id"], bbox_j
                )
                edges.extend(rel_edges)

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _spatial_relations(
        id_a: str, bbox_a: dict, id_b: str, bbox_b: dict
    ) -> list[dict]:
        """Determine spatial edges between two bounding boxes."""
        edges: list[dict] = []
        cx_a, cy_a = _bbox_center(bbox_a)
        cx_b, cy_b = _bbox_center(bbox_b)

        # Contains
        if _bbox_contains(bbox_a, bbox_b):
            edges.append({"source": id_a, "target": id_b, "edge_type": "contains"})
            return edges
        if _bbox_contains(bbox_b, bbox_a):
            edges.append({"source": id_b, "target": id_a, "edge_type": "contains"})
            return edges

        # Overlaps
        if _bbox_overlaps(bbox_a, bbox_b):
            edges.append({"source": id_a, "target": id_b, "edge_type": "overlaps"})

        # Relative position (horizontal)
        if cx_a < cx_b:
            edges.append({"source": id_a, "target": id_b, "edge_type": "left_of"})
        elif cx_a > cx_b:
            edges.append({"source": id_a, "target": id_b, "edge_type": "right_of"})

        # Relative position (vertical)
        if cy_a < cy_b:
            edges.append({"source": id_a, "target": id_b, "edge_type": "above"})
        elif cy_a > cy_b:
            edges.append({"source": id_a, "target": id_b, "edge_type": "below"})

        return edges

    @staticmethod
    def extract_from_video(
        frames: list,
        detections_per_frame: list[list[dict]],
    ) -> dict:
        """Build a scene graph with temporal edges across frames.

        Returns combined graph with 'appears_before', 'appears_after', 'co_occurs' edges.
        """
        all_nodes: list[dict] = []
        all_edges: list[dict] = []

        frame_node_maps: list[dict[str, str]] = []  # label -> node_id per frame

        for frame_idx, dets in enumerate(detections_per_frame):
            label_map: dict[str, str] = {}
            for det_idx, det in enumerate(dets):
                node_id = f"f{frame_idx}_det_{det_idx}"
                label = det.get("class_name", "unknown")
                node = {
                    "id": node_id,
                    "node_type": "object",
                    "label": label,
                    "properties": {
                        "frame": frame_idx,
                        "bbox": det.get("bbox", {}),
                        "confidence": det.get("confidence", 0.0),
                    },
                }
                all_nodes.append(node)
                label_map[label] = node_id
            frame_node_maps.append(label_map)

        # Temporal edges: match by label across consecutive frames
        for fi in range(len(frame_node_maps) - 1):
            cur = frame_node_maps[fi]
            nxt = frame_node_maps[fi + 1]
            for label, cur_id in cur.items():
                if label in nxt:
                    # Same label in consecutive frames → appears_before / co_occurs
                    all_edges.append({"source": cur_id, "target": nxt[label], "edge_type": "appears_before"})
                    all_edges.append({"source": nxt[label], "target": cur_id, "edge_type": "appears_after"})

            # co_occurs: objects in the same frame
            cur_ids = list(cur.values())
            for i in range(len(cur_ids)):
                for j in range(i + 1, len(cur_ids)):
                    all_edges.append({"source": cur_ids[i], "target": cur_ids[j], "edge_type": "co_occurs"})

        # co_occurs for last frame
        if frame_node_maps:
            last_ids = list(frame_node_maps[-1].values())
            for i in range(len(last_ids)):
                for j in range(i + 1, len(last_ids)):
                    all_edges.append({"source": last_ids[i], "target": last_ids[j], "edge_type": "co_occurs"})

        return {"nodes": all_nodes, "edges": all_edges}

    @staticmethod
    def detect_interactions(
        detections: list[dict],
        threshold_distance: float = 50.0,
    ) -> list[dict]:
        """Detect interaction edges — objects within *threshold_distance* pixels."""
        edges: list[dict] = []
        for i in range(len(detections)):
            for j in range(i + 1, len(detections)):
                bbox_i = detections[i].get("bbox", {})
                bbox_j = detections[j].get("bbox", {})
                if not bbox_i or not bbox_j:
                    continue
                dist = _bbox_distance(bbox_i, bbox_j)
                edge_type = "interacts_with" if dist < threshold_distance / 2 else "near"
                if dist < threshold_distance:
                    edges.append({
                        "source": f"det_{i}",
                        "target": f"det_{j}",
                        "edge_type": edge_type,
                        "properties": {"distance": round(dist, 2)},
                    })
        return edges
