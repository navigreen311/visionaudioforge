"""Knowledge Graph routes — nodes, edges, neighbors, scene extraction.

Nodes and edges are rows in ``graph_nodes`` / ``graph_edges``. They used to be
module-level dicts, and every read path had a fabricated fallback: an unknown
id returned a "Mock Node", an empty graph returned three invented edges, and
search always reported three hits. A graph that answers confidently about
entities it does not have is worse than one that returns nothing — those
fallbacks are gone, and missing data now reads as missing.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode

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
    workspace_id: str | None = None


class SceneExtractRequest(BaseModel):
    description: str
    workspace_id: str | None = None


class ExtractRequest(BaseModel):
    """Request body for entity extraction from text."""
    text: str
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise_node(node: GraphNode) -> dict[str, Any]:
    return {
        "id": str(node.id),
        "label": node.label,
        "type": node.node_type,
        "properties": node.properties or {},
        "workspace_id": str(node.workspace_id) if node.workspace_id else None,
    }


def _serialise_edge(edge: GraphEdge) -> dict[str, Any]:
    return {
        "id": str(edge.id),
        "source_id": str(edge.source_id),
        "target_id": str(edge.target_id),
        "relation": edge.relation,
        "weight": edge.weight,
        "properties": edge.properties or {},
    }


def _require_workspace(workspace_id: str | None) -> uuid.UUID:
    """Nodes are workspace-scoped; refuse to create one without a workspace."""
    if not workspace_id:
        raise HTTPException(
            status_code=422,
            detail="workspace_id is required — graph nodes are workspace-scoped",
        )
    try:
        return uuid.UUID(str(workspace_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="workspace_id must be a UUID")


def _as_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field} must be a UUID")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/nodes", status_code=201)
async def add_node(
    body: NodeCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Add a node to the knowledge graph."""
    node = GraphNode(
        label=body.label,
        node_type=body.node_type,
        properties=body.properties or {},
        workspace_id=_require_workspace(body.workspace_id),
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _serialise_node(node)


@router.post("/nodes/batch", status_code=201)
async def add_nodes_batch(
    body: list[NodeCreate],
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create multiple nodes in a single request."""
    nodes = [
        GraphNode(
            label=item.label,
            node_type=item.node_type,
            properties=item.properties or {},
            workspace_id=_require_workspace(item.workspace_id),
        )
        for item in body
    ]
    db.add_all(nodes)
    await db.commit()
    for node in nodes:
        await db.refresh(node)

    created = [_serialise_node(n) for n in nodes]
    return {"created": created, "count": len(created)}


@router.get("/nodes")
async def list_nodes(
    limit: int = Query(100, ge=1, le=1000),
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List nodes, optionally scoped to a workspace."""
    stmt = select(GraphNode)
    if workspace_id is not None:
        stmt = stmt.where(GraphNode.workspace_id == workspace_id)
    rows = (await db.execute(stmt.order_by(GraphNode.created_at).limit(limit))).scalars().all()
    return [_serialise_node(n) for n in rows]


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get a single node by ID."""
    node = (
        await db.execute(
            select(GraphNode).where(GraphNode.id == _as_uuid(node_id, "node_id"))
        )
    ).scalar_one_or_none()

    if node is None:
        # Previously this returned an invented "Mock Node" for any id, so the
        # console could not tell a real entity from one that does not exist.
        raise HTTPException(status_code=404, detail="Node not found")
    return _serialise_node(node)


@router.get("/nodes/{node_id}/edges")
async def get_node_edges(
    node_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get all edges connected to a node."""
    nid = _as_uuid(node_id, "node_id")
    rows = (
        await db.execute(
            select(GraphEdge).where(
                or_(GraphEdge.source_id == nid, GraphEdge.target_id == nid)
            )
        )
    ).scalars().all()

    edges = [_serialise_edge(e) for e in rows]
    return {"node_id": node_id, "edges": edges, "total": len(edges)}


@router.get("/nodes/{node_id}/assets")
async def get_node_assets(
    node_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Assets linked to a node.

    There is no node-to-asset association table yet, so this reports an empty
    list rather than the two invented assets it used to return for every node.
    """
    _as_uuid(node_id, "node_id")
    return {
        "node_id": node_id,
        "assets": [],
        "total": 0,
        "supported": False,
        "detail": "Node-to-asset links are not modelled yet.",
    }


@router.post("/edges", status_code=201)
async def add_edge(
    body: EdgeCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Add an edge between two nodes."""
    source_id = _as_uuid(body.source_id, "source_id")
    target_id = _as_uuid(body.target_id, "target_id")

    # Both endpoints must exist: an edge to a node that was never created is a
    # dangling claim about a relationship.
    found = (
        await db.execute(
            select(GraphNode).where(GraphNode.id.in_([source_id, target_id]))
        )
    ).scalars().all()
    by_id = {n.id: n for n in found}
    for label, nid in (("source_id", source_id), ("target_id", target_id)):
        if nid not in by_id:
            raise HTTPException(status_code=404, detail=f"{label} node not found")

    workspace_id = (
        _require_workspace(body.workspace_id)
        if body.workspace_id
        else by_id[source_id].workspace_id
    )

    edge = GraphEdge(
        source_id=source_id,
        target_id=target_id,
        relation=body.relation,
        weight=body.weight,
        properties=body.properties or {},
        workspace_id=workspace_id,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return _serialise_edge(edge)


@router.get("/edges")
async def list_edges(
    workspace_id: UUID | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List edges, optionally scoped to a workspace."""
    stmt = select(GraphEdge)
    if workspace_id is not None:
        stmt = stmt.where(GraphEdge.workspace_id == workspace_id)
    rows = (await db.execute(stmt.order_by(GraphEdge.created_at).limit(limit))).scalars().all()
    return [_serialise_edge(e) for e in rows]


@router.get("/search")
async def search_nodes(
    q: str = Query("", description="Search query"),
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Search nodes by label.

    An empty result set is reported as empty. This used to return three
    invented node ids whenever nothing matched.
    """
    if not q:
        return {"matching_node_ids": [], "total": 0}

    stmt = select(GraphNode).where(GraphNode.label.ilike(f"%{q}%"))
    if workspace_id is not None:
        stmt = stmt.where(GraphNode.workspace_id == workspace_id)

    rows = (await db.execute(stmt)).scalars().all()
    return {
        "matching_node_ids": [str(n.id) for n in rows],
        "total": len(rows),
    }


@router.get("/autocomplete")
async def autocomplete_nodes(
    q: str = Query("", description="Autocomplete query"),
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Autocomplete node labels for search typeahead."""
    if not q:
        return []

    stmt = select(GraphNode).where(GraphNode.label.ilike(f"%{q}%"))
    if workspace_id is not None:
        stmt = stmt.where(GraphNode.workspace_id == workspace_id)

    rows = (await db.execute(stmt.limit(10))).scalars().all()
    return [
        {"id": str(n.id), "label": n.label, "type": n.node_type} for n in rows
    ]


@router.get("/path")
async def find_path(
    from_node: str = Query(..., alias="from", description="Source node ID"),
    to_node: str = Query(..., alias="to", description="Target node ID"),
    max_hops: int = Query(4, ge=1, le=6),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Find a shortest path between two nodes by breadth-first search.

    Previously this returned a fixed two-hop path through an invented
    "Intermediate Node" regardless of whether any path existed.
    """
    start = _as_uuid(from_node, "from")
    goal = _as_uuid(to_node, "to")

    edges = (await db.execute(select(GraphEdge))).scalars().all()
    adjacency: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
    for e in edges:
        adjacency.setdefault(e.source_id, []).append((e.target_id, e.relation))
        adjacency.setdefault(e.target_id, []).append((e.source_id, e.relation))

    # BFS, tracking the relation used to reach each node.
    queue: list[list[tuple[uuid.UUID, str | None]]] = [[(start, None)]]
    seen = {start}
    path: list[tuple[uuid.UUID, str | None]] | None = None

    while queue:
        current = queue.pop(0)
        node_id, _ = current[-1]
        if node_id == goal:
            path = current
            break
        if len(current) > max_hops:
            continue
        for neighbour, relation in adjacency.get(node_id, []):
            if neighbour in seen:
                continue
            seen.add(neighbour)
            queue.append(current + [(neighbour, relation)])

    if path is None:
        return {"from": from_node, "to": to_node, "hops": 0, "path": [], "found": False}

    labels = {
        n.id: n.label
        for n in (
            await db.execute(
                select(GraphNode).where(GraphNode.id.in_([p[0] for p in path]))
            )
        ).scalars().all()
    }

    return {
        "from": from_node,
        "to": to_node,
        "hops": len(path) - 1,
        "found": True,
        "path": [
            {
                "node_id": str(nid),
                "label": labels.get(nid, ""),
                **({"edge_relation": relation} if relation else {}),
            }
            for nid, relation in path
        ],
    }


@router.post("/extract")
async def extract_entities(body: ExtractRequest) -> dict[str, Any]:
    """Extract entities from text.

    No NER model is wired up, so this reports that rather than returning two
    fixed "Extracted Entity" placeholders as though they came from the text.
    """
    return {
        "text": body.text,
        "entities": [],
        "total": 0,
        "supported": False,
        "detail": "Entity extraction requires an NER model that is not configured.",
    }


@router.get("/export")
async def export_graph(
    format: str = Query("json", description="Export format"),
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Export the knowledge graph. An empty graph exports as empty."""
    node_stmt = select(GraphNode)
    edge_stmt = select(GraphEdge)
    if workspace_id is not None:
        node_stmt = node_stmt.where(GraphNode.workspace_id == workspace_id)
        edge_stmt = edge_stmt.where(GraphEdge.workspace_id == workspace_id)

    nodes = (await db.execute(node_stmt)).scalars().all()
    edges = (await db.execute(edge_stmt)).scalars().all()

    return {
        "format": format,
        "nodes": [_serialise_node(n) for n in nodes],
        "edges": [_serialise_edge(e) for e in edges],
    }


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(
    node_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get all neighbors of a node."""
    nid = _as_uuid(node_id, "node_id")

    node = (
        await db.execute(select(GraphNode).where(GraphNode.id == nid))
    ).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    rows = (
        await db.execute(
            select(GraphEdge).where(
                or_(GraphEdge.source_id == nid, GraphEdge.target_id == nid)
            )
        )
    ).scalars().all()

    neighbors = []
    for e in rows:
        if e.source_id == nid:
            neighbors.append(
                {
                    "node_id": str(e.target_id),
                    "relation": e.relation,
                    "direction": "outgoing",
                }
            )
        else:
            neighbors.append(
                {
                    "node_id": str(e.source_id),
                    "relation": e.relation,
                    "direction": "incoming",
                }
            )

    return {"node_id": node_id, "neighbors": neighbors}


@router.post("/scene-extract")
async def scene_extract(body: SceneExtractRequest) -> dict[str, Any]:
    """Extract entities and relations from a scene description.

    This is a capitalised-word heuristic, not NLP — labelled as such so its
    output is not mistaken for model-extracted entities.
    """
    words = body.description.split()
    entities = [w for w in words if w and w[0].isupper()]
    return {
        "description": body.description,
        "entities_extracted": len(entities),
        "entities": entities,
        "relations": [],
        "method": "capitalisation_heuristic",
    }
