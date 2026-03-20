"""Graph RAG service — retrieval-augmented generation using the knowledge graph."""

import logging
from collections import deque
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_graph.query_parser import GraphQueryParser

logger = logging.getLogger(__name__)


class GraphRAGService:
    """Retrieval-Augmented Generation backed by the knowledge graph.

    Retrieves entity/relationship context from the graph and formats it
    for copilot prompt augmentation.
    """

    def __init__(self) -> None:
        self._parser = GraphQueryParser()

    async def retrieve_context(
        self,
        db: AsyncSession,
        query: str,
        workspace_id: str,
        max_nodes: int = 20,
    ) -> dict[str, Any]:
        """Retrieve graph context relevant to a query.

        Returns:
            {
                "nodes": list[dict],
                "edges": list[dict],
                "context_text": str,
            }
        """
        from app.models.event import Event

        # Parse query for entity names and types
        parsed = self._parser.parse(query)
        search_terms = parsed.get("entities", [])
        entity_type_filter = parsed.get("filters", {}).get("entity_type")

        # Also extract individual words as potential entity references
        query_words = [w.lower() for w in query.split() if len(w) > 2]

        # Fetch graph nodes from DB
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type.like("graph_node_%"),
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(200)
        )
        result = await db.execute(stmt)
        all_nodes = result.scalars().all()

        # Score nodes by label similarity to query
        scored_nodes: list[tuple[float, Any]] = []
        for node in all_nodes:
            payload = node.payload or {}
            label = payload.get("label", "").lower()
            node_type = payload.get("node_type", "unknown")

            if entity_type_filter and node_type != entity_type_filter:
                continue

            score = 0.0
            # Exact entity match
            for term in search_terms:
                if term.lower() in label:
                    score += 10.0
                elif label in term.lower():
                    score += 5.0

            # Word overlap
            for word in query_words:
                if word in label:
                    score += 2.0

            if score > 0:
                scored_nodes.append((score, node))

        # Sort by score, take top max_nodes
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        matched_nodes = [n for _, n in scored_nodes[:max_nodes]]
        matched_node_ids = {str(n.id) for n in matched_nodes}

        # For each matched node, get 1-hop neighbors via edges
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type == "graph_edge",
                )
            )
            .limit(500)
        )
        result = await db.execute(stmt)
        all_edges = result.scalars().all()

        relevant_edges = []
        neighbor_ids: set[str] = set()
        for edge in all_edges:
            payload = edge.payload or {}
            source_id = payload.get("source_id", "")
            target_id = payload.get("target_id", "")
            if source_id in matched_node_ids or target_id in matched_node_ids:
                relevant_edges.append(edge)
                neighbor_ids.add(source_id)
                neighbor_ids.add(target_id)

        # Get neighbor nodes not already matched
        neighbor_nodes = []
        for node in all_nodes:
            nid = str(node.id)
            if nid in neighbor_ids and nid not in matched_node_ids:
                neighbor_nodes.append(node)

        # Build result
        all_result_nodes = matched_nodes + neighbor_nodes
        nodes_out = []
        for node in all_result_nodes:
            payload = node.payload or {}
            nodes_out.append({
                "id": str(node.id),
                "label": payload.get("label", ""),
                "type": payload.get("node_type", "unknown"),
                "properties": payload.get("properties", {}),
                "timestamp": node.timestamp.isoformat() if node.timestamp else "",
            })

        edges_out = []
        for edge in relevant_edges:
            payload = edge.payload or {}
            edges_out.append({
                "id": str(edge.id),
                "source_id": payload.get("source_id", ""),
                "target_id": payload.get("target_id", ""),
                "source_label": payload.get("source_label", ""),
                "target_label": payload.get("target_label", ""),
                "relationship": payload.get("relationship", ""),
                "properties": payload.get("properties", {}),
                "timestamp": edge.timestamp.isoformat() if edge.timestamp else "",
            })

        # Build natural language context text
        context_text = self._build_context_text(nodes_out, edges_out)

        return {
            "nodes": nodes_out,
            "edges": edges_out,
            "context_text": context_text,
        }

    def _build_context_text(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> str:
        """Build natural language context from nodes and edges."""
        if not nodes and not edges:
            return "No relevant knowledge graph context found."

        lines: list[str] = []

        # Describe entities
        if nodes:
            lines.append("Known entities:")
            for node in nodes[:20]:
                props = node.get("properties", {})
                prop_str = ""
                if props:
                    prop_parts = [f"{k}={v}" for k, v in props.items()]
                    prop_str = f" ({', '.join(prop_parts[:5])})"
                lines.append(
                    f"- {node['label']} [{node['type']}]{prop_str}"
                )

        # Describe relationships
        if edges:
            lines.append("")
            lines.append("Relationships:")
            for edge in edges[:30]:
                relationship = edge.get("relationship", "related to")
                source = edge.get("source_label", "Unknown")
                target = edge.get("target_label", "Unknown")
                props = edge.get("properties", {})
                time_str = ""
                if props.get("time"):
                    time_str = f" at time {props['time']}"
                elif props.get("timestamp"):
                    time_str = f" at time {props['timestamp']}"
                location_str = ""
                if props.get("location"):
                    location_str = f" near {props['location']}"
                lines.append(
                    f"- {source} {relationship} {target}{time_str}{location_str}."
                )

        return "\n".join(lines)

    async def augment_copilot_prompt(
        self,
        db: AsyncSession,
        query: str,
        workspace_id: str,
    ) -> str:
        """Retrieve graph context and format it as a copilot prompt augmentation.

        Returns a string to append to the system prompt.
        """
        context = await self.retrieve_context(db, query, workspace_id)
        context_text = context.get("context_text", "")

        if not context_text or context_text == "No relevant knowledge graph context found.":
            return ""

        return (
            "KNOWLEDGE GRAPH CONTEXT:\n"
            f"{context_text}\n\n"
            "Use this context to answer the query. Reference specific entities "
            "and relationships from the knowledge graph when relevant."
        )

    async def query_graph_nl(
        self,
        db: AsyncSession,
        question: str,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Answer a natural language question using the knowledge graph.

        Returns:
            {
                "answer": str,
                "evidence_nodes": list,
                "confidence": float,
            }
        """
        parsed = self._parser.parse(question)
        query_result = await self._parser.execute(db, parsed, workspace_id)

        results = query_result.get("results", [])
        query_type = query_result.get("query_type", "unknown")

        if not results:
            return {
                "answer": f"No information found in the knowledge graph for: {question}",
                "evidence_nodes": [],
                "confidence": 0.0,
            }

        # Build answer based on query type
        answer_parts: list[str] = []
        evidence_nodes: list[dict] = []
        confidence = 0.0

        if query_type == "find_entity":
            answer_parts.append(f"Found {len(results)} matching entities:")
            for r in results[:10]:
                answer_parts.append(f"- {r.get('label', 'Unknown')} ({r.get('type', 'unknown')})")
                evidence_nodes.append(r)
            confidence = min(0.9, 0.3 + len(results) * 0.1)

        elif query_type == "find_relationship":
            answer_parts.append(f"Found {len(results)} relationships:")
            for r in results[:10]:
                answer_parts.append(
                    f"- {r.get('source', '?')} {r.get('relationship', 'related to')} "
                    f"{r.get('target', '?')}"
                )
                evidence_nodes.append(r)
            confidence = min(0.9, 0.3 + len(results) * 0.1)

        elif query_type == "find_path":
            if results:
                path_result = results[0]
                path_nodes = path_result.get("path", [])
                distance = path_result.get("distance", 0)
                labels = [n.get("label", "?") for n in path_nodes]
                answer_parts.append(
                    f"Connection found (distance {distance}): "
                    f"{' -> '.join(labels)}"
                )
                evidence_nodes = path_nodes
                confidence = 0.85

        elif query_type == "temporal_query":
            answer_parts.append(f"Found {len(results)} events in the timeline:")
            for r in results[:10]:
                answer_parts.append(
                    f"- [{r.get('timestamp', '?')}] {r.get('label', 'Unknown')}"
                )
                evidence_nodes.append(r)
            confidence = min(0.8, 0.2 + len(results) * 0.1)

        elif query_type == "find_pattern":
            answer_parts.append(f"Found {len(results)} patterns:")
            for r in results[:10]:
                answer_parts.append(
                    f"- {r.get('pattern', '?')} (count: {r.get('count', 0)})"
                )
            confidence = min(0.7, 0.2 + len(results) * 0.05)

        answer = "\n".join(answer_parts) if answer_parts else "No answer could be constructed."

        return {
            "answer": answer,
            "evidence_nodes": evidence_nodes,
            "confidence": round(confidence, 2),
        }

    async def build_entity_summary(
        self,
        db: AsyncSession,
        entity_node_id: str,
    ) -> dict[str, Any]:
        """Build a comprehensive summary for an entity node.

        Returns:
            {
                "entity": str,
                "type": str,
                "relationships": list,
                "timeline": list,
                "related_events": list,
                "summary_text": str,
            }
        """
        from app.models.event import Event

        # Get the entity node
        stmt = select(Event).where(Event.id == entity_node_id)
        result = await db.execute(stmt)
        node_event = result.scalar_one_or_none()

        if not node_event:
            return {
                "entity": "Unknown",
                "type": "unknown",
                "relationships": [],
                "timeline": [],
                "related_events": [],
                "summary_text": f"Entity {entity_node_id} not found.",
            }

        payload = node_event.payload or {}
        entity_label = payload.get("label", "Unknown")
        entity_type = payload.get("node_type", "unknown")
        properties = payload.get("properties", {})

        # Get all edges connected to this entity
        workspace_id = str(node_event.workspace_id)
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type == "graph_edge",
                )
            )
            .order_by(Event.timestamp.asc())
            .limit(200)
        )
        result = await db.execute(stmt)
        all_edges = result.scalars().all()

        relationships = []
        timeline = []
        related_events = []

        for edge in all_edges:
            edge_payload = edge.payload or {}
            source_id = edge_payload.get("source_id", "")
            target_id = edge_payload.get("target_id", "")

            if source_id == entity_node_id or target_id == entity_node_id:
                rel = {
                    "id": str(edge.id),
                    "relationship": edge_payload.get("relationship", ""),
                    "source_label": edge_payload.get("source_label", ""),
                    "target_label": edge_payload.get("target_label", ""),
                    "direction": "outgoing" if source_id == entity_node_id else "incoming",
                    "properties": edge_payload.get("properties", {}),
                }
                relationships.append(rel)

                # Build timeline entry
                if edge.timestamp:
                    timeline.append({
                        "timestamp": edge.timestamp.isoformat(),
                        "event": (
                            f"{edge_payload.get('source_label', '?')} "
                            f"{edge_payload.get('relationship', 'related to')} "
                            f"{edge_payload.get('target_label', '?')}"
                        ),
                    })

                # Track related events
                other_label = (
                    edge_payload.get("target_label", "")
                    if source_id == entity_node_id
                    else edge_payload.get("source_label", "")
                )
                if other_label:
                    related_events.append({
                        "entity": other_label,
                        "relationship": edge_payload.get("relationship", ""),
                        "timestamp": edge.timestamp.isoformat() if edge.timestamp else "",
                    })

        # Sort timeline chronologically
        timeline.sort(key=lambda x: x["timestamp"])

        # Build summary text
        summary_parts = [f"{entity_label} is a {entity_type}."]

        if properties:
            prop_str = ", ".join(f"{k}: {v}" for k, v in properties.items())
            summary_parts.append(f"Properties: {prop_str}.")

        if relationships:
            summary_parts.append(f"Has {len(relationships)} known relationships.")
            for rel in relationships[:5]:
                if rel["direction"] == "outgoing":
                    summary_parts.append(
                        f"- {entity_label} {rel['relationship']} {rel['target_label']}."
                    )
                else:
                    summary_parts.append(
                        f"- {rel['source_label']} {rel['relationship']} {entity_label}."
                    )

        if timeline:
            summary_parts.append(
                f"Activity spans from {timeline[0]['timestamp']} to {timeline[-1]['timestamp']}."
            )

        return {
            "entity": entity_label,
            "type": entity_type,
            "relationships": relationships,
            "timeline": timeline,
            "related_events": related_events,
            "summary_text": " ".join(summary_parts),
        }

    async def find_path(
        self,
        db: AsyncSession,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """Find the shortest path between two nodes using BFS.

        Returns:
            {
                "path": list[dict],
                "edges": list[dict],
                "distance": int,
            }
        """
        from app.models.event import Event

        # Get source and target nodes
        stmt = select(Event).where(Event.id.in_([source_id, target_id]))
        result = await db.execute(stmt)
        target_nodes = {str(e.id): e for e in result.scalars().all()}

        if source_id not in target_nodes or target_id not in target_nodes:
            missing = []
            if source_id not in target_nodes:
                missing.append(f"source={source_id}")
            if target_id not in target_nodes:
                missing.append(f"target={target_id}")
            return {
                "path": [],
                "edges": [],
                "distance": -1,
                "error": f"Node(s) not found: {', '.join(missing)}",
            }

        source_event = target_nodes[source_id]
        workspace_id = str(source_event.workspace_id)

        # Load all edges for this workspace
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type == "graph_edge",
                )
            )
            .limit(1000)
        )
        result = await db.execute(stmt)
        all_edges = result.scalars().all()

        # Build adjacency list
        adjacency: dict[str, list[tuple[str, dict]]] = {}
        edge_lookup: dict[str, dict] = {}

        for edge in all_edges:
            payload = edge.payload or {}
            src = payload.get("source_id", "")
            tgt = payload.get("target_id", "")
            edge_info = {
                "id": str(edge.id),
                "source_id": src,
                "target_id": tgt,
                "source_label": payload.get("source_label", ""),
                "target_label": payload.get("target_label", ""),
                "relationship": payload.get("relationship", ""),
                "properties": payload.get("properties", {}),
            }
            edge_lookup[str(edge.id)] = edge_info
            adjacency.setdefault(src, []).append((tgt, edge_info))
            adjacency.setdefault(tgt, []).append((src, edge_info))

        # Load all nodes for label resolution
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type.like("graph_node_%"),
                )
            )
            .limit(500)
        )
        result = await db.execute(stmt)
        all_node_events = result.scalars().all()
        node_info: dict[str, dict] = {}
        for ne in all_node_events:
            p = ne.payload or {}
            node_info[str(ne.id)] = {
                "id": str(ne.id),
                "label": p.get("label", ""),
                "type": p.get("node_type", "unknown"),
                "properties": p.get("properties", {}),
            }

        # BFS shortest path
        queue: deque[tuple[str, list[str], list[dict]]] = deque(
            [(source_id, [source_id], [])]
        )
        visited = {source_id}

        while queue:
            current, path, path_edges = queue.popleft()

            if len(path) > max_depth + 1:
                continue

            if current == target_id:
                path_nodes = []
                for nid in path:
                    info = node_info.get(nid, {"id": nid, "label": nid, "type": "unknown"})
                    path_nodes.append(info)
                return {
                    "path": path_nodes,
                    "edges": path_edges,
                    "distance": len(path) - 1,
                }

            for neighbor_id, edge_info in adjacency.get(current, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((
                        neighbor_id,
                        path + [neighbor_id],
                        path_edges + [edge_info],
                    ))

        return {
            "path": [],
            "edges": [],
            "distance": -1,
            "error": "No path found between the specified nodes.",
        }
