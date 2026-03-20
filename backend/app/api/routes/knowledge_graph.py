"""Knowledge graph API routes — RAG queries, entity summaries, path finding, and NL queries."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.knowledge_graph.graph_rag import GraphRAGService
from app.services.knowledge_graph.query_parser import GraphQueryParser

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])

graph_rag_service = GraphRAGService()
query_parser = GraphQueryParser()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RAGQueryRequest(BaseModel):
    question: str
    workspace_id: str = "00000000-0000-0000-0000-000000000001"


class RAGContextRequest(BaseModel):
    query: str
    workspace_id: str = "00000000-0000-0000-0000-000000000001"


class PathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = 5


class NLQueryRequest(BaseModel):
    query: str
    workspace_id: str = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/rag/query")
async def rag_query(
    body: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Natural language query against the knowledge graph with evidence."""
    result = await graph_rag_service.query_graph_nl(
        db, body.question, body.workspace_id
    )
    return result


@router.post("/rag/context")
async def rag_context(
    body: RAGContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve graph context for copilot prompt augmentation."""
    context = await graph_rag_service.retrieve_context(
        db, body.query, body.workspace_id
    )
    return context


@router.get("/entity/{entity_id}/summary")
async def entity_summary(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a comprehensive summary for an entity node."""
    result = await graph_rag_service.build_entity_summary(db, entity_id)
    if result.get("entity") == "Unknown" and "not found" in result.get("summary_text", ""):
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return result


@router.post("/path")
async def find_path(
    body: PathRequest,
    db: AsyncSession = Depends(get_db),
):
    """Find shortest path between two graph nodes."""
    result = await graph_rag_service.find_path(
        db, body.source_id, body.target_id, body.max_depth
    )
    return result


@router.post("/nl-query")
async def nl_query(
    body: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse and execute a natural language graph query."""
    parsed = query_parser.parse(body.query)
    result = await query_parser.execute(db, parsed, body.workspace_id)
    return {
        "parsed": parsed,
        "results": result.get("results", []),
        "query_type": result.get("query_type", "unknown"),
    }
