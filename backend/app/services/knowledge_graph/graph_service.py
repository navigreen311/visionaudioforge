"""Core Knowledge Graph service — CRUD operations, traversal, and merge."""

from __future__ import annotations

import uuid
from collections import deque
from typing import Optional

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode


class KnowledgeGraphService:
    """Provides async graph manipulation over the relational store."""

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def add_node(
        db: AsyncSession,
        node_type: str,
        label: str,
        properties: dict,
        workspace_id: uuid.UUID,
        embedding: Optional[bytes] = None,
    ) -> GraphNode:
        """Create and persist a new graph node."""
        node = GraphNode(
            node_type=node_type,
            label=label,
            properties=properties or {},
            embedding=embedding,
            workspace_id=workspace_id,
        )
        db.add(node)
        await db.flush()
        await db.refresh(node)
        return node

    @staticmethod
    async def get_node(db: AsyncSession, node_id: uuid.UUID) -> GraphNode:
        """Return a node with its edges eagerly loaded."""
        stmt = (
            select(GraphNode)
            .options(
                selectinload(GraphNode.outgoing_edges),
                selectinload(GraphNode.incoming_edges),
            )
            .where(GraphNode.id == node_id)
        )
        result = await db.execute(stmt)
        node = result.scalar_one_or_none()
        if node is None:
            raise ValueError(f"GraphNode {node_id} not found")
        return node

    @staticmethod
    async def search_nodes(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        node_type: Optional[str] = None,
        label_query: Optional[str] = None,
        limit: int = 50,
    ) -> list[GraphNode]:
        """Search nodes by workspace with optional filters."""
        stmt = select(GraphNode).where(GraphNode.workspace_id == workspace_id)
        if node_type:
            stmt = stmt.where(GraphNode.node_type == node_type)
        if label_query:
            stmt = stmt.where(GraphNode.label.ilike(f"%{label_query}%"))
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete_node(db: AsyncSession, node_id: uuid.UUID) -> None:
        """Delete a node and cascade-delete its edges."""
        # Edges are cascade-deleted via FK ondelete, but also clean up explicitly
        await db.execute(
            delete(GraphEdge).where(
                or_(GraphEdge.source_id == node_id, GraphEdge.target_id == node_id)
            )
        )
        await db.execute(delete(GraphNode).where(GraphNode.id == node_id))
        await db.flush()

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def add_edge(
        db: AsyncSession,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        edge_type: str,
        properties: Optional[dict] = None,
        confidence: float = 1.0,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> GraphEdge:
        """Create a directed edge between two nodes."""
        # Infer workspace from source node if not provided
        if workspace_id is None:
            src = await db.get(GraphNode, source_id)
            if src is None:
                raise ValueError(f"Source node {source_id} not found")
            workspace_id = src.workspace_id

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
            confidence=confidence,
            workspace_id=workspace_id,
        )
        db.add(edge)
        await db.flush()
        await db.refresh(edge)
        return edge

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    @staticmethod
    async def get_neighbors(
        db: AsyncSession,
        node_id: uuid.UUID,
        edge_type: Optional[str] = None,
        depth: int = 1,
    ) -> list[GraphNode]:
        """BFS traversal returning connected nodes up to *depth* hops."""
        visited: set[uuid.UUID] = {node_id}
        queue: deque[tuple[uuid.UUID, int]] = deque([(node_id, 0)])
        neighbors: list[GraphNode] = []

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            # Outgoing
            stmt = select(GraphEdge).where(GraphEdge.source_id == current_id)
            if edge_type:
                stmt = stmt.where(GraphEdge.edge_type == edge_type)
            result = await db.execute(stmt)
            out_edges = list(result.scalars().all())

            # Incoming
            stmt = select(GraphEdge).where(GraphEdge.target_id == current_id)
            if edge_type:
                stmt = stmt.where(GraphEdge.edge_type == edge_type)
            result = await db.execute(stmt)
            in_edges = list(result.scalars().all())

            neighbor_ids = set()
            for e in out_edges:
                neighbor_ids.add(e.target_id)
            for e in in_edges:
                neighbor_ids.add(e.source_id)

            for nid in neighbor_ids:
                if nid not in visited:
                    visited.add(nid)
                    node = await db.get(GraphNode, nid)
                    if node:
                        neighbors.append(node)
                        queue.append((nid, current_depth + 1))

        return neighbors

    # ------------------------------------------------------------------
    # Subgraph
    # ------------------------------------------------------------------

    @staticmethod
    async def get_subgraph(
        db: AsyncSession, node_ids: list[uuid.UUID]
    ) -> dict:
        """Return the induced subgraph for the given node IDs."""
        stmt = select(GraphNode).where(GraphNode.id.in_(node_ids))
        result = await db.execute(stmt)
        nodes = list(result.scalars().all())

        stmt = select(GraphEdge).where(
            GraphEdge.source_id.in_(node_ids),
            GraphEdge.target_id.in_(node_ids),
        )
        result = await db.execute(stmt)
        edges = list(result.scalars().all())

        return {
            "nodes": [
                {"id": str(n.id), "node_type": n.node_type, "label": n.label, "properties": n.properties}
                for n in nodes
            ],
            "edges": [
                {
                    "id": str(e.id),
                    "source_id": str(e.source_id),
                    "target_id": str(e.target_id),
                    "edge_type": e.edge_type,
                    "confidence": e.confidence,
                    "properties": e.properties,
                }
                for e in edges
            ],
        }

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    @staticmethod
    async def merge_nodes(
        db: AsyncSession,
        node_ids: list[uuid.UUID],
        merged_label: Optional[str] = None,
    ) -> GraphNode:
        """Merge multiple nodes into one, combining properties and redirecting edges."""
        if len(node_ids) < 2:
            raise ValueError("Need at least 2 nodes to merge")

        stmt = select(GraphNode).where(GraphNode.id.in_(node_ids))
        result = await db.execute(stmt)
        nodes = list(result.scalars().all())
        if len(nodes) < 2:
            raise ValueError("Not enough valid nodes found to merge")

        # The first node becomes the survivor
        survivor = nodes[0]
        merged_props: dict = {}
        for n in nodes:
            if n.properties:
                merged_props.update(n.properties)

        survivor.properties = merged_props
        if merged_label:
            survivor.label = merged_label

        # Redirect edges from absorbed nodes to survivor
        absorbed_ids = [n.id for n in nodes[1:]]
        await db.execute(
            update(GraphEdge)
            .where(GraphEdge.source_id.in_(absorbed_ids))
            .values(source_id=survivor.id)
        )
        await db.execute(
            update(GraphEdge)
            .where(GraphEdge.target_id.in_(absorbed_ids))
            .values(target_id=survivor.id)
        )

        # Remove self-loops that may have formed
        await db.execute(
            delete(GraphEdge).where(
                GraphEdge.source_id == survivor.id,
                GraphEdge.target_id == survivor.id,
            )
        )

        # Delete absorbed nodes
        await db.execute(delete(GraphNode).where(GraphNode.id.in_(absorbed_ids)))
        await db.flush()
        await db.refresh(survivor)
        return survivor
