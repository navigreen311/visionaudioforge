"""Pipeline execution engine — validation, topological sort, and execution."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from app.services.pipeline.nodes import NODE_REGISTRY, get_node


class PipelineEngine:
    """Validates and executes node-graph pipeline definitions."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_pipeline(self, definition: dict) -> dict[str, Any]:
        """Validate a pipeline definition.

        Returns ``{"valid": bool, "errors": list[str]}``.
        """
        errors: list[str] = []
        nodes = definition.get("nodes", [])
        edges = definition.get("edges", [])

        if not nodes:
            errors.append("Pipeline must contain at least one node.")
            return {"valid": False, "errors": errors}

        node_ids = {n["id"] for n in nodes}

        # Check node types exist
        for node in nodes:
            ntype = node.get("type")
            if ntype not in NODE_REGISTRY:
                errors.append(f"Unknown node type '{ntype}' on node '{node.get('id')}'.")

        # Check edges reference valid node ids
        for edge in edges:
            if edge.get("from") not in node_ids:
                errors.append(f"Edge references unknown source node '{edge.get('from')}'.")
            if edge.get("to") not in node_ids:
                errors.append(f"Edge references unknown target node '{edge.get('to')}'.")

        # Check for cycles via topological sort
        try:
            self._topological_sort(nodes, edges)
        except ValueError as exc:
            errors.append(str(exc))

        # Check required params
        for node in nodes:
            ntype = node.get("type")
            if ntype in NODE_REGISTRY:
                instance = get_node(ntype)
                params = node.get("params", {})
                for key, spec in instance.input_schema.items():
                    if spec.get("required") and key not in params:
                        # Input ports that will be filled by edges are OK
                        has_incoming_edge = any(
                            e.get("to") == node["id"] and e.get("to_port") == key
                            for e in edges
                        )
                        if not has_incoming_edge:
                            errors.append(
                                f"Node '{node['id']}' ({ntype}) missing required param '{key}'."
                            )

        return {"valid": len(errors) == 0, "errors": errors}

    # ------------------------------------------------------------------
    # Topological sort — Kahn's algorithm
    # ------------------------------------------------------------------

    def _topological_sort(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> list[str]:
        """Return node IDs in topological execution order (Kahn's algorithm)."""
        node_ids = [n["id"] for n in nodes]
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adjacency: dict[str, list[str]] = defaultdict(list)

        for edge in edges:
            src, dst = edge["from"], edge["to"]
            adjacency[src].append(dst)
            in_degree[dst] = in_degree.get(dst, 0) + 1

        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbour in adjacency[nid]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if len(order) != len(node_ids):
            raise ValueError("Pipeline contains a cycle.")

        return order

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_pipeline(self, definition: dict) -> dict[str, Any]:
        """Execute a validated pipeline definition.

        Returns::

            {
                "status": "completed" | "failed",
                "node_results": {node_id: output_dict, ...},
                "duration_ms": float,
                "errors": [str, ...],
            }
        """
        validation = self.validate_pipeline(definition)
        if not validation["valid"]:
            return {
                "status": "failed",
                "node_results": {},
                "duration_ms": 0,
                "errors": validation["errors"],
            }

        nodes = definition["nodes"]
        edges = definition.get("edges", [])

        node_map = {n["id"]: n for n in nodes}
        order = self._topological_sort(nodes, edges)

        # Build reverse edge lookup: dst_id → [(src_id, from_port, to_port)]
        incoming: dict[str, list[dict]] = defaultdict(list)
        for edge in edges:
            incoming[edge["to"]].append(edge)

        node_results: dict[str, dict] = {}
        errors: list[str] = []
        t0 = time.perf_counter()

        for nid in order:
            node_def = node_map[nid]
            node_instance = get_node(node_def["type"])

            # Gather inputs: start with static params, overlay upstream outputs
            inputs = dict(node_def.get("params", {}))
            for edge in incoming.get(nid, []):
                src_output = node_results.get(edge["from"], {})
                from_port = edge.get("from_port", "output")
                to_port = edge.get("to_port", "input")
                value = src_output.get(from_port, src_output)
                inputs[to_port] = value

            result = await node_instance.execute(inputs)
            node_results[nid] = result

            if "error" in result:
                errors.append(f"Node '{nid}' ({node_def['type']}): {result['error']}")

        duration_ms = (time.perf_counter() - t0) * 1000
        status = "failed" if errors else "completed"

        return {
            "status": status,
            "node_results": node_results,
            "duration_ms": round(duration_ms, 2),
            "errors": errors,
        }
