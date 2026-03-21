"""Knowledge Graph routes — nodes, edges, neighbors, scene extraction."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    label: str
    node_type: str = "entity"
    properties: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None


class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class SceneExtractRequest(BaseModel):
    description: str
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# In-memory store (replaced by DB in production)
# ---------------------------------------------------------------------------
_nodes: dict[str, dict] = {}
_edges: list[dict] = []
_counter = 0


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"node-{_counter:06d}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/nodes")
async def add_node(body: NodeCreate) -> dict[str, Any]:
    """Add a node to the knowledge graph."""
    nid = _next_id()
    node = {"id": nid, "label": body.label, "type": body.node_type, "properties": body.properties}
    _nodes[nid] = node
    return node


@router.get("/nodes")
async def list_nodes(limit: int = Query(100, ge=1, le=1000)) -> list[dict]:
    """List all nodes."""
    return list(_nodes.values())[:limit]


@router.get("/nodes/{node_id}")
async def get_node(node_id: str) -> dict[str, Any]:
    """Get a single node by ID with full detail."""
    if node_id in _nodes:
        node = _nodes[node_id]
        return {
            **node,
            "created_at": node.get("created_at", "2025-01-15T10:00:00Z"),
            "updated_at": node.get("updated_at", "2025-01-15T12:30:00Z"),
        }
    # Return mock data for demo node IDs
    mock_nodes: dict[str, dict[str, Any]] = {
        "p1": {"id": "p1", "label": "John Smith", "type": "person", "properties": {"role": "suspect", "age": "34", "height": "5'11\"", "status": "active"}},
        "p2": {"id": "p2", "label": "Jane Doe", "type": "person", "properties": {"role": "witness", "age": "28"}},
        "p3": {"id": "p3", "label": "Officer Lee", "type": "person", "properties": {"role": "investigator", "badge": "4521"}},
        "l1": {"id": "l1", "label": "Main Street", "type": "location", "properties": {"district": "downtown", "lat": "40.7128", "lng": "-74.0060"}},
        "l2": {"id": "l2", "label": "Warehouse 5", "type": "location", "properties": {"district": "industrial", "capacity": "large"}},
        "v1": {"id": "v1", "label": "Red Sedan", "type": "vehicle", "properties": {"plate": "ABC-1234", "color": "red", "make": "Toyota", "model": "Camry"}},
        "v2": {"id": "v2", "label": "White Van", "type": "vehicle", "properties": {"plate": "XYZ-5678", "color": "white"}},
        "o1": {"id": "o1", "label": "Backpack", "type": "object", "properties": {"color": "black", "brand": "North Face"}},
        "e1": {"id": "e1", "label": "Incident #42", "type": "event", "properties": {"time": "2025-01-15 10:30", "severity": "high"}},
        "e2": {"id": "e2", "label": "Traffic Stop", "type": "event", "properties": {"time": "2025-01-15 11:00"}},
    }
    if node_id in mock_nodes:
        return {
            **mock_nodes[node_id],
            "created_at": "2025-01-15T08:00:00Z",
            "updated_at": "2025-01-15T12:30:00Z",
        }
    raise HTTPException(status_code=404, detail="Node not found")


@router.get("/nodes/{node_id}/edges")
async def get_node_edges(node_id: str) -> dict[str, Any]:
    """Get all edges connected to a node."""
    # Check real store first
    connected: list[dict[str, Any]] = []
    for e in _edges:
        if e["source_id"] == node_id:
            target = _nodes.get(e["target_id"], {})
            connected.append({
                "id": f"edge-{e['source_id']}-{e['target_id']}",
                "relationship": e["relation"],
                "direction": "outgoing",
                "connected_node_id": e["target_id"],
                "connected_node_label": target.get("label", e["target_id"]),
                "connected_node_type": target.get("type", "unknown"),
            })
        elif e["target_id"] == node_id:
            source = _nodes.get(e["source_id"], {})
            connected.append({
                "id": f"edge-{e['source_id']}-{e['target_id']}",
                "relationship": e["relation"],
                "direction": "incoming",
                "connected_node_id": e["source_id"],
                "connected_node_label": source.get("label", e["source_id"]),
                "connected_node_type": source.get("type", "unknown"),
            })

    if connected:
        return {"node_id": node_id, "edges": connected}

    # Return mock edges for demo IDs
    _mock_edges: list[dict[str, str]] = [
        {"id": "e-1", "src": "p1", "tgt": "l1", "src_label": "John Smith", "tgt_label": "Main Street", "rel": "was seen at", "src_type": "person", "tgt_type": "location"},
        {"id": "e-2", "src": "p1", "tgt": "v1", "src_label": "John Smith", "tgt_label": "Red Sedan", "rel": "drove", "src_type": "person", "tgt_type": "vehicle"},
        {"id": "e-3", "src": "p2", "tgt": "l1", "src_label": "Jane Doe", "tgt_label": "Main Street", "rel": "witnessed at", "src_type": "person", "tgt_type": "location"},
        {"id": "e-4", "src": "p1", "tgt": "o1", "src_label": "John Smith", "tgt_label": "Backpack", "rel": "carried", "src_type": "person", "tgt_type": "object"},
        {"id": "e-5", "src": "v1", "tgt": "l2", "src_label": "Red Sedan", "tgt_label": "Warehouse 5", "rel": "parked at", "src_type": "vehicle", "tgt_type": "location"},
        {"id": "e-6", "src": "p3", "tgt": "e1", "src_label": "Officer Lee", "tgt_label": "Incident #42", "rel": "responded to", "src_type": "person", "tgt_type": "event"},
        {"id": "e-7", "src": "e1", "tgt": "l1", "src_label": "Incident #42", "tgt_label": "Main Street", "rel": "occurred at", "src_type": "event", "tgt_type": "location"},
        {"id": "e-8", "src": "v2", "tgt": "l2", "src_label": "White Van", "tgt_label": "Warehouse 5", "rel": "spotted near", "src_type": "vehicle", "tgt_type": "location"},
        {"id": "e-9", "src": "p3", "tgt": "e2", "src_label": "Officer Lee", "tgt_label": "Traffic Stop", "rel": "conducted", "src_type": "person", "tgt_type": "event"},
        {"id": "e-10", "src": "e2", "tgt": "v1", "src_label": "Traffic Stop", "tgt_label": "Red Sedan", "rel": "involved", "src_type": "event", "tgt_type": "vehicle"},
    ]
    result: list[dict[str, str]] = []
    for me in _mock_edges:
        if me["src"] == node_id:
            result.append({
                "id": me["id"],
                "relationship": me["rel"],
                "direction": "outgoing",
                "connected_node_id": me["tgt"],
                "connected_node_label": me["tgt_label"],
                "connected_node_type": me["tgt_type"],
            })
        elif me["tgt"] == node_id:
            result.append({
                "id": me["id"],
                "relationship": me["rel"],
                "direction": "incoming",
                "connected_node_id": me["src"],
                "connected_node_label": me["src_label"],
                "connected_node_type": me["src_type"],
            })
    return {"node_id": node_id, "edges": result}


@router.get("/nodes/{node_id}/assets")
async def get_node_assets(node_id: str) -> dict[str, Any]:
    """Get assets linked to a node."""
    # Mock data for demo
    mock_assets: dict[str, list[dict[str, str | None]]] = {
        "p1": [
            {"id": "asset-001", "filename": "surveillance_cam3.mp4", "thumbnail_url": None, "media_type": "video/mp4"},
            {"id": "asset-002", "filename": "witness_photo.jpg", "thumbnail_url": None, "media_type": "image/jpeg"},
        ],
        "l1": [
            {"id": "asset-003", "filename": "street_view.jpg", "thumbnail_url": None, "media_type": "image/jpeg"},
        ],
        "e1": [
            {"id": "asset-004", "filename": "incident_report.pdf", "thumbnail_url": None, "media_type": "application/pdf"},
            {"id": "asset-005", "filename": "body_cam_footage.mp4", "thumbnail_url": None, "media_type": "video/mp4"},
        ],
    }
    return {"node_id": node_id, "assets": mock_assets.get(node_id, [])}


@router.post("/edges")
async def add_edge(body: EdgeCreate) -> dict[str, Any]:
    """Add an edge between two nodes."""
    edge = {
        "source_id": body.source_id,
        "target_id": body.target_id,
        "relation": body.relation,
        "weight": body.weight,
        "properties": body.properties,
    }
    _edges.append(edge)
    return edge


@router.get("/edges")
async def list_edges() -> list[dict]:
    """List all edges."""
    return _edges


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(node_id: str) -> dict[str, Any]:
    """Get all neighbors of a node."""
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    neighbors = []
    for e in _edges:
        if e["source_id"] == node_id:
            neighbors.append({"node_id": e["target_id"], "relation": e["relation"], "direction": "outgoing"})
        elif e["target_id"] == node_id:
            neighbors.append({"node_id": e["source_id"], "relation": e["relation"], "direction": "incoming"})
    return {"node_id": node_id, "neighbors": neighbors}


@router.get("/search")
async def search_nodes(q: str = Query("", min_length=1)) -> dict[str, list[str] | int]:
    """Search nodes by label (case-insensitive substring match)."""
    query = q.lower()
    matched_ids = [
        nid
        for nid, node in _nodes.items()
        if query in node.get("label", "").lower()
        or query in node.get("type", "").lower()
        or any(query in str(v).lower() for v in node.get("properties", {}).values())
    ]
    return {"node_ids": matched_ids, "total": len(matched_ids)}


@router.get("/autocomplete")
async def autocomplete_nodes(
    q: str = Query("", min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict[str, str]]:
    """Return autocomplete suggestions matching query prefix."""
    query = q.lower()
    results: list[dict[str, str]] = []
    for nid, node in _nodes.items():
        label = node.get("label", "")
        if query in label.lower():
            results.append({"id": nid, "label": label, "type": node.get("type", "unknown")})
            if len(results) >= limit:
                break
    return results


@router.post("/scene-extract")
async def scene_extract(body: SceneExtractRequest) -> dict[str, Any]:
    """Extract entities and relations from a scene description."""
    # Stub: in production, uses NLP to extract entities
    words = body.description.split()
    entities = [w for w in words if w[0].isupper()] if words else []
    return {
        "description": body.description,
        "entities_extracted": len(entities),
        "entities": entities,
        "relations": [],
    }
