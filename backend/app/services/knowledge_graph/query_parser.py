"""Graph query language parser — translates natural language into structured graph queries."""

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class GraphQueryParser:
    """Parse natural language queries into structured graph operations.

    Supports intents: find_entity, find_relationship, find_path,
    find_pattern, temporal_query.
    """

    # Pattern templates for intent detection
    INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
        ("find_path", re.compile(
            r"how\s+is\s+(.+?)\s+connected\s+to\s+(.+)",
            re.IGNORECASE,
        )),
        ("find_path", re.compile(
            r"(?:find|show)\s+(?:the\s+)?path\s+(?:from|between)\s+(.+?)\s+(?:to|and)\s+(.+)",
            re.IGNORECASE,
        )),
        ("temporal_query", re.compile(
            r"what\s+happened\s+(?:near|at|in)\s+(.+?)\s+between\s+(.+?)\s+and\s+(.+)",
            re.IGNORECASE,
        )),
        ("temporal_query", re.compile(
            r"what\s+happened\s+(?:after|before|since)\s+(.+)",
            re.IGNORECASE,
        )),
        ("find_relationship", re.compile(
            r"who\s+(?:was|is)\s+(?:near|at|with|related\s+to)\s+(.+)",
            re.IGNORECASE,
        )),
        ("find_relationship", re.compile(
            r"what\s+(?:is|are)\s+(?:connected|related|linked)\s+to\s+(.+)",
            re.IGNORECASE,
        )),
        ("find_pattern", re.compile(
            r"(?:find|show)\s+(?:all\s+)?(?:patterns?|clusters?|groups?)\s+(?:of|for|in)\s+(.+)",
            re.IGNORECASE,
        )),
        ("find_entity", re.compile(
            r"(?:find|show|list|get)\s+(?:all\s+)?(\w+(?:\s+\w+)?)",
            re.IGNORECASE,
        )),
    ]

    # Entity type keywords
    ENTITY_TYPES = {
        "person": ["person", "people", "individual", "suspect", "witness", "man", "woman"],
        "object": ["object", "item", "thing", "weapon", "bag", "package", "device"],
        "location": ["location", "place", "area", "zone", "building", "room", "street"],
        "event": ["event", "incident", "occurrence", "activity", "action"],
        "vehicle": ["vehicle", "car", "truck", "van", "bus", "motorcycle", "bike"],
    }

    def parse(self, query: str) -> dict[str, Any]:
        """Parse a natural language query into a structured graph query.

        Returns:
            {
                "intent": str,
                "entities": list[str],
                "filters": dict,
                "traversal": dict,
                "raw_query": str,
            }
        """
        query = query.strip()
        result: dict[str, Any] = {
            "intent": "find_entity",
            "entities": [],
            "filters": {},
            "traversal": {},
            "raw_query": query,
        }

        # Try each pattern to detect intent
        for intent, pattern in self.INTENT_PATTERNS:
            match = pattern.search(query)
            if match:
                result["intent"] = intent
                groups = [g.strip() for g in match.groups() if g]
                result["entities"] = groups

                if intent == "find_path":
                    result["traversal"] = {
                        "source": groups[0] if len(groups) > 0 else None,
                        "target": groups[1] if len(groups) > 1 else None,
                        "max_depth": 5,
                    }
                elif intent == "temporal_query":
                    result["filters"]["temporal"] = True
                    if len(groups) >= 3:
                        result["filters"]["location"] = groups[0]
                        result["filters"]["time_start"] = groups[1]
                        result["filters"]["time_end"] = groups[2]
                    elif len(groups) >= 1:
                        result["filters"]["time_reference"] = groups[0]

                break

        # Extract entity type filters from query
        query_lower = query.lower()
        for entity_type, keywords in self.ENTITY_TYPES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    result["filters"]["entity_type"] = entity_type
                    break
            if "entity_type" in result["filters"]:
                break

        # Extract quoted entity names
        quoted = re.findall(r'"([^"]+)"', query)
        if quoted:
            result["entities"] = quoted + result["entities"]

        return result

    async def execute(
        self,
        db: AsyncSession,
        parsed_query: dict[str, Any],
        workspace_id: str,
    ) -> dict[str, Any]:
        """Execute a parsed graph query against the database.

        Returns:
            {"results": list, "query_type": str}
        """
        intent = parsed_query["intent"]
        entities = parsed_query.get("entities", [])
        filters = parsed_query.get("filters", {})
        traversal = parsed_query.get("traversal", {})

        try:
            from app.models.event import Event

            if intent == "find_entity":
                return await self._execute_find_entity(
                    db, entities, filters, workspace_id
                )
            elif intent == "find_relationship":
                return await self._execute_find_relationship(
                    db, entities, filters, workspace_id
                )
            elif intent == "find_path":
                return await self._execute_find_path(
                    db, traversal, workspace_id
                )
            elif intent == "temporal_query":
                return await self._execute_temporal_query(
                    db, entities, filters, workspace_id
                )
            elif intent == "find_pattern":
                return await self._execute_find_pattern(
                    db, entities, filters, workspace_id
                )
            else:
                return {"results": [], "query_type": intent}

        except Exception as exc:
            logger.warning("Graph query execution failed: %s", exc)
            return {"results": [], "query_type": intent, "error": str(exc)}

    async def _execute_find_entity(
        self,
        db: AsyncSession,
        entities: list[str],
        filters: dict,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Find entities matching the query terms."""
        from app.models.event import Event

        entity_type = filters.get("entity_type")

        conditions = [Event.workspace_id == workspace_id]
        if entity_type:
            conditions.append(Event.type == f"graph_node_{entity_type}")

        # Search in payload for entity names
        if entities:
            name_conditions = []
            for name in entities:
                name_conditions.append(
                    func.cast(Event.payload, type_=db.bind.dialect.type_descriptor(
                        type(Event.payload.type)
                    )).ilike(f"%{name}%")
                    if hasattr(Event.payload, "ilike")
                    else Event.type.ilike(f"%graph_node%")
                )

        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type.like("graph_node_%"),
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(50)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        # Filter by entity names in payload
        matches = []
        for event in events:
            payload = event.payload or {}
            label = payload.get("label", "").lower()
            if not entities or any(e.lower() in label for e in entities):
                if not entity_type or payload.get("node_type") == entity_type:
                    matches.append({
                        "id": str(event.id),
                        "label": payload.get("label", ""),
                        "type": payload.get("node_type", "unknown"),
                        "properties": payload.get("properties", {}),
                        "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                    })

        return {"results": matches, "query_type": "find_entity"}

    async def _execute_find_relationship(
        self,
        db: AsyncSession,
        entities: list[str],
        filters: dict,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Find relationships connected to specified entities."""
        from app.models.event import Event

        # Get graph edges
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type == "graph_edge",
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(100)
        )
        result = await db.execute(stmt)
        edges = result.scalars().all()

        matches = []
        for edge in edges:
            payload = edge.payload or {}
            source_label = payload.get("source_label", "").lower()
            target_label = payload.get("target_label", "").lower()

            if not entities or any(
                e.lower() in source_label or e.lower() in target_label
                for e in entities
            ):
                matches.append({
                    "id": str(edge.id),
                    "source": payload.get("source_label", ""),
                    "target": payload.get("target_label", ""),
                    "relationship": payload.get("relationship", ""),
                    "properties": payload.get("properties", {}),
                    "timestamp": edge.timestamp.isoformat() if edge.timestamp else "",
                })

        return {"results": matches, "query_type": "find_relationship"}

    async def _execute_find_path(
        self,
        db: AsyncSession,
        traversal: dict,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Find path between two entities using BFS."""
        source_name = traversal.get("source", "")
        target_name = traversal.get("target", "")
        max_depth = traversal.get("max_depth", 5)

        if not source_name or not target_name:
            return {"results": [], "query_type": "find_path", "error": "Source and target required"}

        # Build adjacency from graph edges
        from app.models.event import Event

        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    or_(
                        Event.type == "graph_edge",
                        Event.type.like("graph_node_%"),
                    ),
                )
            )
            .limit(500)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        # Build graph
        nodes: dict[str, dict] = {}
        adjacency: dict[str, list[tuple[str, dict]]] = {}

        for event in events:
            payload = event.payload or {}
            if event.type.startswith("graph_node_"):
                node_id = str(event.id)
                label = payload.get("label", "")
                nodes[node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": payload.get("node_type", "unknown"),
                }
                # Index by label for lookup
                nodes[label.lower()] = nodes[node_id]
            elif event.type == "graph_edge":
                src_id = payload.get("source_id", "")
                tgt_id = payload.get("target_id", "")
                edge_info = {
                    "id": str(event.id),
                    "relationship": payload.get("relationship", ""),
                }
                adjacency.setdefault(src_id, []).append((tgt_id, edge_info))
                adjacency.setdefault(tgt_id, []).append((src_id, edge_info))

        # Find source/target node IDs by label
        source_node = nodes.get(source_name.lower())
        target_node = nodes.get(target_name.lower())

        if not source_node or not target_node:
            return {
                "results": [],
                "query_type": "find_path",
                "error": f"Could not find nodes: source='{source_name}', target='{target_name}'",
            }

        # BFS
        from collections import deque

        source_id = source_node["id"]
        target_id = target_node["id"]
        queue: deque[tuple[str, list[str], list[dict]]] = deque(
            [(source_id, [source_id], [])]
        )
        visited = {source_id}

        while queue:
            current, path, edges_in_path = queue.popleft()
            if len(path) > max_depth + 1:
                break

            if current == target_id:
                path_nodes = []
                for nid in path:
                    node = nodes.get(nid, {"id": nid, "label": nid, "type": "unknown"})
                    path_nodes.append(node)
                return {
                    "results": [{
                        "path": path_nodes,
                        "edges": edges_in_path,
                        "distance": len(path) - 1,
                    }],
                    "query_type": "find_path",
                }

            for neighbor_id, edge_info in adjacency.get(current, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((
                        neighbor_id,
                        path + [neighbor_id],
                        edges_in_path + [edge_info],
                    ))

        return {"results": [], "query_type": "find_path", "error": "No path found"}

    async def _execute_temporal_query(
        self,
        db: AsyncSession,
        entities: list[str],
        filters: dict,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Find events in a time range, optionally near a location."""
        from app.models.event import Event

        conditions = [
            Event.workspace_id == workspace_id,
            or_(
                Event.type.like("graph_node_%"),
                Event.type == "graph_edge",
            ),
        ]

        stmt = (
            select(Event)
            .where(and_(*conditions))
            .order_by(Event.timestamp.asc())
            .limit(100)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        location_filter = filters.get("location", "").lower()
        matches = []
        for event in events:
            payload = event.payload or {}
            label = payload.get("label", "").lower()
            source_label = payload.get("source_label", "").lower()
            target_label = payload.get("target_label", "").lower()

            if location_filter and location_filter not in label and \
               location_filter not in source_label and location_filter not in target_label:
                continue

            matches.append({
                "id": str(event.id),
                "type": event.type,
                "label": payload.get("label", payload.get("relationship", "")),
                "properties": payload.get("properties", {}),
                "timestamp": event.timestamp.isoformat() if event.timestamp else "",
            })

        return {"results": matches, "query_type": "temporal_query"}

    async def _execute_find_pattern(
        self,
        db: AsyncSession,
        entities: list[str],
        filters: dict,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Find co-occurring patterns in the graph."""
        from app.models.event import Event

        stmt = (
            select(Event)
            .where(
                and_(
                    Event.workspace_id == workspace_id,
                    Event.type == "graph_edge",
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(200)
        )
        result = await db.execute(stmt)
        edges = result.scalars().all()

        # Count co-occurrences
        co_occurrence: dict[str, int] = {}
        for edge in edges:
            payload = edge.payload or {}
            key = f"{payload.get('source_label', '')} <-> {payload.get('target_label', '')}"
            co_occurrence[key] = co_occurrence.get(key, 0) + 1

        # Return top patterns
        sorted_patterns = sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)
        results = [
            {"pattern": k, "count": v}
            for k, v in sorted_patterns[:20]
        ]

        return {"results": results, "query_type": "find_pattern"}
