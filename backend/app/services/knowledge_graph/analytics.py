"""Graph analytics — centrality, community detection, anomaly detection, and temporal analysis."""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode


class GraphAnalytics:
    """Analytical queries over the knowledge graph."""

    # ------------------------------------------------------------------
    # Centrality
    # ------------------------------------------------------------------

    @staticmethod
    async def centrality(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        method: str = "degree",
    ) -> list[dict]:
        """Compute centrality scores for nodes in a workspace.

        Methods:
          - 'degree': count of edges per node
          - 'betweenness': stub (returns 0.0 for all)
        """
        stmt = select(GraphNode).where(GraphNode.workspace_id == workspace_id)
        result = await db.execute(stmt)
        nodes = list(result.scalars().all())
        node_ids = {n.id for n in nodes}

        if method == "degree":
            # Count edges per node
            degree_map: dict[uuid.UUID, int] = defaultdict(int)

            stmt_edges = select(GraphEdge).where(GraphEdge.workspace_id == workspace_id)
            result = await db.execute(stmt_edges)
            edges = list(result.scalars().all())

            for e in edges:
                if e.source_id in node_ids:
                    degree_map[e.source_id] += 1
                if e.target_id in node_ids:
                    degree_map[e.target_id] += 1

            scores = [
                {"node_id": str(n.id), "label": n.label, "score": float(degree_map.get(n.id, 0))}
                for n in nodes
            ]
            scores.sort(key=lambda x: x["score"], reverse=True)
            return scores

        elif method == "betweenness":
            # Stub: return 0.0 for all
            return [
                {"node_id": str(n.id), "label": n.label, "score": 0.0}
                for n in nodes
            ]

        return []

    # ------------------------------------------------------------------
    # Community Detection
    # ------------------------------------------------------------------

    @staticmethod
    async def community_detection(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict]:
        """Detect communities using connected components (BFS)."""
        stmt = select(GraphNode).where(GraphNode.workspace_id == workspace_id)
        result = await db.execute(stmt)
        nodes = list(result.scalars().all())
        node_ids = {n.id for n in nodes}
        node_map = {n.id: n for n in nodes}

        # Build adjacency list
        adj: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        stmt_edges = select(GraphEdge).where(GraphEdge.workspace_id == workspace_id)
        result = await db.execute(stmt_edges)
        edges = list(result.scalars().all())

        for e in edges:
            if e.source_id in node_ids and e.target_id in node_ids:
                adj[e.source_id].add(e.target_id)
                adj[e.target_id].add(e.source_id)

        visited: set[uuid.UUID] = set()
        communities: list[dict] = []
        community_id = 0

        for nid in node_ids:
            if nid in visited:
                continue
            # BFS
            component: list[uuid.UUID] = []
            queue: deque[uuid.UUID] = deque([nid])
            visited.add(nid)
            while queue:
                cur = queue.popleft()
                component.append(cur)
                for neighbor in adj.get(cur, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            communities.append({
                "community_id": community_id,
                "nodes": [
                    {"node_id": str(cid), "label": node_map[cid].label}
                    for cid in component
                    if cid in node_map
                ],
            })
            community_id += 1

        return communities

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    @staticmethod
    async def anomaly_detection(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict]:
        """Flag nodes with unusual connectivity."""
        degree_scores = await GraphAnalytics.centrality(db, workspace_id, method="degree")

        if not degree_scores:
            return []

        avg_degree = sum(s["score"] for s in degree_scores) / len(degree_scores)
        anomalies: list[dict] = []

        for s in degree_scores:
            reasons: list[str] = []
            anomaly_score = 0.0

            if s["score"] == 0:
                reasons.append("isolated_node")
                anomaly_score = 0.8
            elif avg_degree > 0 and s["score"] > 3 * avg_degree:
                reasons.append("high_degree_hub")
                anomaly_score = min(1.0, s["score"] / (3 * avg_degree) * 0.5 + 0.5)

            if reasons:
                anomalies.append({
                    "node_id": s["node_id"],
                    "label": s["label"],
                    "anomaly_score": round(anomaly_score, 4),
                    "reason": ", ".join(reasons),
                    "degree": s["score"],
                })

        anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return anomalies

    # ------------------------------------------------------------------
    # Temporal Analysis
    # ------------------------------------------------------------------

    @staticmethod
    async def temporal_analysis(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> dict:
        """Analyse graph growth and key events in a time window."""
        # Node count over time
        stmt = (
            select(
                func.date_trunc("hour", GraphNode.created_at).label("hour"),
                func.count(GraphNode.id).label("cnt"),
            )
            .where(
                GraphNode.workspace_id == workspace_id,
                GraphNode.created_at >= start,
                GraphNode.created_at <= end,
            )
            .group_by("hour")
            .order_by("hour")
        )
        result = await db.execute(stmt)
        node_counts = [
            {"time": row.hour.isoformat() if row.hour else None, "count": row.cnt}
            for row in result
        ]

        # Edge growth
        stmt = (
            select(
                func.date_trunc("hour", GraphEdge.created_at).label("hour"),
                func.count(GraphEdge.id).label("cnt"),
            )
            .where(
                GraphEdge.workspace_id == workspace_id,
                GraphEdge.created_at >= start,
                GraphEdge.created_at <= end,
            )
            .group_by("hour")
            .order_by("hour")
        )
        result = await db.execute(stmt)
        edge_counts = [
            {"time": row.hour.isoformat() if row.hour else None, "count": row.cnt}
            for row in result
        ]

        # Key events: event-type nodes created in window
        stmt = (
            select(GraphNode)
            .where(
                GraphNode.workspace_id == workspace_id,
                GraphNode.node_type == "event",
                GraphNode.created_at >= start,
                GraphNode.created_at <= end,
            )
            .order_by(GraphNode.created_at)
            .limit(50)
        )
        result = await db.execute(stmt)
        key_events = [
            {
                "node_id": str(n.id),
                "label": n.label,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in result.scalars().all()
        ]

        return {
            "node_count_over_time": node_counts,
            "edge_growth": edge_counts,
            "key_events": key_events,
        }
