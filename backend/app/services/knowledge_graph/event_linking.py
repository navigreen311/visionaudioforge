"""Event linking — cross-camera linking, causal chains, and pattern detection."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.knowledge_graph import GraphEdge, GraphNode


class EventLinker:
    """Links events into knowledge graph edges for temporal, causal, and cross-camera relationships."""

    @staticmethod
    async def link_events(
        db: AsyncSession,
        events: list[Any],
        time_window_s: float = 30.0,
    ) -> list[GraphEdge]:
        """Link events within a time window.

        Creates edges:
          - 'co_occurs': events within time_window_s of each other
          - 'follows': sequential events (earlier → later)
          - 'same_source': events from the same source
        """
        created_edges: list[GraphEdge] = []

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        for i in range(len(sorted_events)):
            for j in range(i + 1, len(sorted_events)):
                ev_i = sorted_events[i]
                ev_j = sorted_events[j]

                diff = abs((ev_j.timestamp - ev_i.timestamp).total_seconds())
                if diff > time_window_s:
                    continue

                # Ensure nodes exist for these events
                node_i = await EventLinker._ensure_event_node(db, ev_i)
                node_j = await EventLinker._ensure_event_node(db, ev_j)

                # co_occurs
                edge = GraphEdge(
                    source_id=node_i.id,
                    target_id=node_j.id,
                    edge_type="co_occurs",
                    properties={"time_diff_s": diff},
                    confidence=max(0.0, 1.0 - diff / time_window_s),
                    workspace_id=ev_i.workspace_id,
                )
                db.add(edge)
                created_edges.append(edge)

                # follows (temporal order)
                edge_follows = GraphEdge(
                    source_id=node_i.id,
                    target_id=node_j.id,
                    edge_type="follows",
                    properties={"time_diff_s": diff},
                    confidence=1.0,
                    workspace_id=ev_i.workspace_id,
                )
                db.add(edge_follows)
                created_edges.append(edge_follows)

                # same_source
                if ev_i.source == ev_j.source:
                    edge_src = GraphEdge(
                        source_id=node_i.id,
                        target_id=node_j.id,
                        edge_type="same_source",
                        properties={"source": ev_i.source},
                        confidence=1.0,
                        workspace_id=ev_i.workspace_id,
                    )
                    db.add(edge_src)
                    created_edges.append(edge_src)

        await db.flush()
        return created_edges

    @staticmethod
    async def cross_camera_link(
        db: AsyncSession,
        events_cam1: list[Any],
        events_cam2: list[Any],
        overlap_threshold: float = 0.5,
    ) -> list[dict]:
        """Match events across two cameras by type overlap and time proximity."""
        linked_pairs: list[dict] = []

        for ev1 in events_cam1:
            for ev2 in events_cam2:
                # Time overlap check
                diff = abs((ev1.timestamp - ev2.timestamp).total_seconds())
                time_score = max(0.0, 1.0 - diff / 60.0)  # Decay over 60s

                # Type similarity
                type_match = 1.0 if ev1.type == ev2.type else 0.0

                combined_score = (time_score + type_match) / 2.0

                if combined_score >= overlap_threshold:
                    node1 = await EventLinker._ensure_event_node(db, ev1)
                    node2 = await EventLinker._ensure_event_node(db, ev2)

                    edge = GraphEdge(
                        source_id=node1.id,
                        target_id=node2.id,
                        edge_type="same_as",
                        properties={
                            "cross_camera": True,
                            "time_diff_s": diff,
                            "score": combined_score,
                        },
                        confidence=combined_score,
                        workspace_id=ev1.workspace_id,
                    )
                    db.add(edge)
                    linked_pairs.append({
                        "event_1": str(ev1.id),
                        "event_2": str(ev2.id),
                        "score": combined_score,
                    })

        await db.flush()
        return linked_pairs

    @staticmethod
    async def build_causal_chain(
        db: AsyncSession,
        event_id: uuid.UUID,
        depth: int = 5,
    ) -> dict:
        """Follow 'causes'/'follows' edges forward from an event to build a causal chain."""
        chain: list[dict] = []
        accumulated_confidence = 1.0

        # Find the graph node for this event
        stmt = select(GraphNode).where(
            GraphNode.node_type == "event",
            GraphNode.properties["event_id"].as_string() == str(event_id),
        )
        result = await db.execute(stmt)
        current_node = result.scalar_one_or_none()

        if current_node is None:
            return {"chain": [], "confidence": 0.0}

        visited: set[uuid.UUID] = set()
        current_id = current_node.id

        for _ in range(depth):
            if current_id in visited:
                break
            visited.add(current_id)

            node = await db.get(GraphNode, current_id)
            if not node:
                break

            chain.append({
                "node_id": str(node.id),
                "label": node.label,
                "properties": node.properties,
            })

            # Find outgoing causal/follows edges
            stmt = (
                select(GraphEdge)
                .where(
                    GraphEdge.source_id == current_id,
                    GraphEdge.edge_type.in_(["causes", "follows"]),
                )
                .order_by(GraphEdge.created_at)
                .limit(1)
            )
            result = await db.execute(stmt)
            edge = result.scalar_one_or_none()
            if edge is None:
                break

            accumulated_confidence *= edge.confidence
            current_id = edge.target_id

        return {"chain": chain, "confidence": round(accumulated_confidence, 4)}

    @staticmethod
    async def detect_patterns(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        pattern_type: str = "repeated",
    ) -> list[dict]:
        """Detect event patterns in the graph.

        'repeated': find event type sequences occurring >3 times.
        """
        patterns: list[dict] = []

        if pattern_type == "repeated":
            # Get all event nodes ordered by creation
            stmt = (
                select(GraphNode)
                .where(
                    GraphNode.workspace_id == workspace_id,
                    GraphNode.node_type == "event",
                )
                .order_by(GraphNode.created_at)
            )
            result = await db.execute(stmt)
            event_nodes = list(result.scalars().all())

            # Build sequences of event labels
            labels = [n.label for n in event_nodes]

            # Find repeated bigrams
            bigrams: list[str] = []
            for i in range(len(labels) - 1):
                bigrams.append(f"{labels[i]} -> {labels[i + 1]}")

            counts = Counter(bigrams)
            for pattern, count in counts.most_common():
                if count > 3:
                    patterns.append({
                        "pattern": pattern,
                        "count": count,
                        "type": "repeated_sequence",
                    })

        return patterns

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _ensure_event_node(db: AsyncSession, event: Any) -> GraphNode:
        """Get or create a GraphNode for an Event."""
        stmt = select(GraphNode).where(
            GraphNode.node_type == "event",
            GraphNode.properties["event_id"].as_string() == str(event.id),
        )
        result = await db.execute(stmt)
        node = result.scalar_one_or_none()
        if node:
            return node

        node = GraphNode(
            node_type="event",
            label=event.type,
            properties={
                "event_id": str(event.id),
                "source": event.source,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            },
            workspace_id=event.workspace_id,
        )
        db.add(node)
        await db.flush()
        await db.refresh(node)
        return node
