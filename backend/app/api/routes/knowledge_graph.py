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


@router.get("/path")
async def find_shortest_path(
    from_node: str = Query(..., alias="from", description="Source node ID"),
    to_node: str = Query(..., alias="to", description="Target node ID"),
) -> dict[str, Any]:
    """Find the shortest path between two nodes (BFS).

    Returns a mock 2-hop path as a stub when nodes are not in the store,
    or performs real BFS when the nodes exist.
    """
    # If both nodes exist in our store, do real BFS
    if from_node in _nodes and to_node in _nodes:
        # Build adjacency list
        adj: dict[str, list[str]] = {nid: [] for nid in _nodes}
        for e in _edges:
            src, tgt = e["source_id"], e["target_id"]
            if src in adj and tgt in adj:
                adj[src].append(tgt)
                adj[tgt].append(src)

        # BFS
        visited: set[str] = {from_node}
        parent: dict[str, str] = {}
        queue: list[str] = [from_node]
        found = False

        while queue:
            current = queue.pop(0)
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    if neighbor == to_node:
                        found = True
                        break
                    queue.append(neighbor)
            if found:
                break

        if not found:
            raise HTTPException(status_code=404, detail="No path found")

        # Reconstruct path
        path: list[str] = []
        cur = to_node
        while cur != from_node:
            path.append(cur)
            cur = parent[cur]
        path.append(from_node)
        path.reverse()

        return {"path": path, "hops": len(path) - 1}

    # Stub: return mock 2-hop path for demo
    mid = "mid-stub"
    return {
        "path": [from_node, mid, to_node],
        "hops": 2,
    }


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
