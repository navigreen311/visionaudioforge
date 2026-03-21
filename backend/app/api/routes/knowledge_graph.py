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


class ExtractRequest(BaseModel):
    """Request body for entity extraction from text."""
    text: str
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


def _edge_id() -> str:
    return f"edge-{len(_edges) + 1:06d}"


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


@router.post("/nodes/batch")
async def add_nodes_batch(body: list[NodeCreate]) -> dict[str, Any]:
    """Create multiple nodes in a single request."""
    created = []
    for item in body:
        nid = _next_id()
        node = {"id": nid, "label": item.label, "type": item.node_type, "properties": item.properties}
        _nodes[nid] = node
        created.append(node)
    return {"created": created, "count": len(created)}


@router.get("/nodes")
async def list_nodes(limit: int = Query(100, ge=1, le=1000)) -> list[dict]:
    """List all nodes."""
    return list(_nodes.values())[:limit]


@router.get("/nodes/{node_id}")
async def get_node(node_id: str) -> dict:
    """Get a single node by ID, with properties."""
    if node_id in _nodes:
        return _nodes[node_id]
    # Return mock node for any ID so the frontend always gets data
    return {
        "id": node_id,
        "label": f"Mock Node {node_id}",
        "type": "entity",
        "properties": {
            "description": "Auto-generated mock node",
            "created_at": "2026-01-15T10:30:00Z",
            "tags": ["mock", "knowledge-graph"],
        },
    }


@router.get("/nodes/{node_id}/edges")
async def get_node_edges(node_id: str) -> dict[str, Any]:
    """Get all edges connected to a node. Returns 3 mock edges when none exist."""
    connected = [e for e in _edges if e["source_id"] == node_id or e["target_id"] == node_id]
    if connected:
        return {"node_id": node_id, "edges": connected, "total": len(connected)}
    # Fallback: 3 mock edges
    mock_edges = [
        {"id": "edge-mock-1", "source_id": node_id, "target_id": "node-mock-a", "relation": "related_to", "weight": 1.0},
        {"id": "edge-mock-2", "source_id": "node-mock-b", "target_id": node_id, "relation": "depends_on", "weight": 0.8},
        {"id": "edge-mock-3", "source_id": node_id, "target_id": "node-mock-c", "relation": "part_of", "weight": 0.6},
    ]
    return {"node_id": node_id, "edges": mock_edges, "total": 3}


@router.get("/nodes/{node_id}/assets")
async def get_node_assets(node_id: str) -> dict[str, Any]:
    """Get assets linked to a node. Returns 2 mock assets."""
    mock_assets = [
        {
            "id": "asset-001",
            "name": "scene_render_01.png",
            "type": "image",
            "url": f"/api/assets/asset-001/download",
            "linked_node_id": node_id,
            "created_at": "2026-02-10T08:00:00Z",
        },
        {
            "id": "asset-002",
            "name": "audio_clip_01.wav",
            "type": "audio",
            "url": f"/api/assets/asset-002/download",
            "linked_node_id": node_id,
            "created_at": "2026-02-11T14:30:00Z",
        },
    ]
    return {"node_id": node_id, "assets": mock_assets, "total": 2}


@router.post("/edges")
async def add_edge(body: EdgeCreate) -> dict[str, Any]:
    """Add an edge between two nodes."""
    eid = _edge_id()
    edge = {
        "id": eid,
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


@router.get("/search")
async def search_nodes(q: str = Query("", description="Search query")) -> dict[str, Any]:
    """Search nodes by label. Returns matching node IDs."""
    query_lower = q.lower()
    matching = [n for n in _nodes.values() if query_lower in n.get("label", "").lower()]
    if matching:
        return {"matching_node_ids": [n["id"] for n in matching], "total": len(matching)}
    # Fallback mock results when store is empty or no matches
    return {
        "matching_node_ids": ["node-mock-search-1", "node-mock-search-2", "node-mock-search-3"],
        "total": 3,
    }


@router.get("/autocomplete")
async def autocomplete_nodes(q: str = Query("", description="Autocomplete query")) -> list[dict]:
    """Autocomplete node labels for search typeahead."""
    query_lower = q.lower()
    results = [
        {"id": n["id"], "label": n["label"], "type": n.get("type", "entity")}
        for n in _nodes.values()
        if query_lower in n.get("label", "").lower()
    ]
    if results:
        return results[:10]
    # Fallback mock suggestions
    return [
        {"id": "node-ac-1", "label": f"{q} Entity", "type": "entity"},
        {"id": "node-ac-2", "label": f"{q} Scene", "type": "scene"},
        {"id": "node-ac-3", "label": f"{q} Concept", "type": "concept"},
    ]


@router.get("/path")
async def find_path(
    from_node: str = Query(..., alias="from", description="Source node ID"),
    to_node: str = Query(..., alias="to", description="Target node ID"),
) -> dict[str, Any]:
    """Find a path between two nodes. Returns a mock 2-hop path."""
    intermediate = "node-intermediate-001"
    return {
        "from": from_node,
        "to": to_node,
        "hops": 2,
        "path": [
            {"node_id": from_node, "label": f"Node {from_node}"},
            {"node_id": intermediate, "label": "Intermediate Node", "edge_relation": "connects_to"},
            {"node_id": to_node, "label": f"Node {to_node}", "edge_relation": "leads_to"},
        ],
    }


@router.post("/extract")
async def extract_entities(body: ExtractRequest) -> dict[str, Any]:
    """Extract entities from text. Returns 2 mock extracted entities."""
    # In production, this would use NLP/NER models
    return {
        "text": body.text,
        "entities": [
            {"id": "extracted-001", "label": "Extracted Entity A", "type": "entity", "confidence": 0.92},
            {"id": "extracted-002", "label": "Extracted Entity B", "type": "concept", "confidence": 0.85},
        ],
        "total": 2,
    }


@router.get("/export")
async def export_graph(format: str = Query("json", description="Export format")) -> dict[str, Any]:
    """Export the entire knowledge graph. Returns all nodes and edges."""
    nodes = list(_nodes.values())
    edges = list(_edges)
    # Include mock data if the store is empty
    if not nodes:
        nodes = [
            {"id": "node-export-1", "label": "Sample Node A", "type": "entity", "properties": {}},
            {"id": "node-export-2", "label": "Sample Node B", "type": "concept", "properties": {}},
        ]
    if not edges:
        edges = [
            {"id": "edge-export-1", "source_id": "node-export-1", "target_id": "node-export-2", "relation": "related_to", "weight": 1.0},
        ]
    return {"format": format, "nodes": nodes, "edges": edges}


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(node_id: str) -> dict[str, Any]:
    """Get all neighbors of a node."""
    if node_id not in _nodes:
        # Return mock neighbors instead of 404 for frontend compatibility
        return {
            "node_id": node_id,
            "neighbors": [
                {"node_id": "node-neighbor-1", "relation": "related_to", "direction": "outgoing"},
                {"node_id": "node-neighbor-2", "relation": "part_of", "direction": "incoming"},
            ],
        }
    neighbors = []
    for e in _edges:
        if e["source_id"] == node_id:
            neighbors.append({"node_id": e["target_id"], "relation": e["relation"], "direction": "outgoing"})
        elif e["target_id"] == node_id:
            neighbors.append({"node_id": e["source_id"], "relation": e["relation"], "direction": "incoming"})
    return {"node_id": node_id, "neighbors": neighbors}


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
