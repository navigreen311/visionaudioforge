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
async def get_node(node_id: str) -> dict:
    """Get a single node by ID."""
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    return _nodes[node_id]


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
