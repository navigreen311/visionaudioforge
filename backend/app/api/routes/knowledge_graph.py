"""Knowledge Graph routes — nodes, edges, scene extraction, event linking, and analytics."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.knowledge_graph import (
    CentralityItem,
    CommunityItem,
    AnomalyItem,
    EventLinkRequest,
    GraphEdgeCreate,
    GraphEdgeRead,
    GraphNodeCreate,
    GraphNodeRead,
    SceneExtractRequest,
    SceneGraphResponse,
)
from app.services.knowledge_graph.analytics import GraphAnalytics
from app.services.knowledge_graph.event_linking import EventLinker
from app.services.knowledge_graph.graph_service import KnowledgeGraphService
from app.services.knowledge_graph.scene_extractor import SceneGraphExtractor

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])

# ------------------------------------------------------------------
# Node endpoints
# ------------------------------------------------------------------


@router.post("/nodes", response_model=GraphNodeRead, status_code=201)
async def add_node(
    body: GraphNodeCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new graph node."""
    node = await KnowledgeGraphService.add_node(
        db,
        node_type=body.node_type,
        label=body.label,
        properties=body.properties,
        workspace_id=body.workspace_id,
    )
    await db.commit()
    return node


@router.get("/nodes", response_model=list[GraphNodeRead])
async def search_nodes(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    node_type: Optional[str] = Query(None),
    label_query: Optional[str] = Query(None, alias="q"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    """Search nodes by workspace with optional filters."""
    return await KnowledgeGraphService.search_nodes(
        db, workspace_id, node_type=node_type, label_query=label_query, limit=limit
    )


@router.get("/nodes/{node_id}", response_model=GraphNodeRead)
async def get_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single node with its edges."""
    try:
        return await KnowledgeGraphService.get_node(db, node_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/nodes/{node_id}/neighbors", response_model=list[GraphNodeRead])
async def get_neighbors(
    node_id: UUID,
    depth: int = Query(1, ge=1, le=10),
    edge_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """Get neighbor nodes via BFS traversal."""
    return await KnowledgeGraphService.get_neighbors(
        db, node_id, edge_type=edge_type, depth=depth
    )


# ------------------------------------------------------------------
# Edge endpoints
# ------------------------------------------------------------------


@router.post("/edges", response_model=GraphEdgeRead, status_code=201)
async def add_edge(
    body: GraphEdgeCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a directed edge between two nodes."""
    try:
        edge = await KnowledgeGraphService.add_edge(
            db,
            source_id=body.source_id,
            target_id=body.target_id,
            edge_type=body.edge_type,
            properties=body.properties,
            confidence=body.confidence,
            workspace_id=body.workspace_id,
        )
        await db.commit()
        return edge
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------
# Scene extraction
# ------------------------------------------------------------------


@router.post("/extract-scene", response_model=SceneGraphResponse)
async def extract_scene(
    body: SceneExtractRequest,
):
    """Extract a scene graph from detections."""
    detections = [d.model_dump() for d in body.detections]
    result = SceneGraphExtractor.extract_scene_graph(image=None, detections=detections)
    return result


# ------------------------------------------------------------------
# Event linking
# ------------------------------------------------------------------


@router.post("/link-events", response_model=dict)
async def link_events(
    body: EventLinkRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Link events within a time window."""
    from sqlalchemy import select
    from app.models.event import Event

    stmt = select(Event).where(Event.id.in_(body.event_ids))
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    if not events:
        return {"edges_created": 0}

    edges = await EventLinker.link_events(db, events, time_window_s=body.time_window)
    await db.commit()
    return {"edges_created": len(edges)}


# ------------------------------------------------------------------
# Subgraph
# ------------------------------------------------------------------


@router.get("/subgraph", response_model=dict)
async def get_subgraph(
    node_ids: str = Query(..., description="Comma-separated node UUIDs"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the induced subgraph for given node IDs."""
    ids = [UUID(nid.strip()) for nid in node_ids.split(",") if nid.strip()]
    return await KnowledgeGraphService.get_subgraph(db, ids)


# ------------------------------------------------------------------
# Analytics
# ------------------------------------------------------------------


@router.get("/analytics/centrality", response_model=list[CentralityItem])
async def centrality(
    workspace_id: UUID = Query(...),
    method: str = Query("degree"),
    db: AsyncSession = Depends(get_async_session),
):
    """Compute centrality scores for workspace nodes."""
    return await GraphAnalytics.centrality(db, workspace_id, method=method)


@router.get("/analytics/communities", response_model=list[CommunityItem])
async def communities(
    workspace_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Detect communities via connected components."""
    return await GraphAnalytics.community_detection(db, workspace_id)


@router.get("/analytics/anomalies", response_model=list[AnomalyItem])
async def anomalies(
    workspace_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Detect anomalous nodes by connectivity patterns."""
    return await GraphAnalytics.anomaly_detection(db, workspace_id)
