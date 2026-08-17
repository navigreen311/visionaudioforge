"""Custom Pipeline Node SDK — create, validate, register, and test custom nodes."""

from __future__ import annotations

import ast
import logging
import time
import textwrap
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import CustomNode

logger = logging.getLogger(__name__)


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None

# Custom node definitions live in the custom_nodes table. Scaffolded code has
# to outlive the request that produced it — a pipeline referencing a node whose
# definition is gone cannot run.

NODE_TEMPLATE = textwrap.dedent("""\
    from visionaudioforge.pipeline import BaseNode


    class {class_name}Node(BaseNode):
        name = "{name}"
        category = "{category}"
        description = "{description}"
        input_schema = {{"data": "any"}}
        output_schema = {{"result": "any"}}

        async def execute(self, inputs):
            # Your implementation here
            processed_data = inputs.get("data")
            return {{"result": processed_data}}
""")


class CustomNodeSDK:
    """SDK for creating, validating, registering, and testing custom pipeline nodes."""

    # ------------------------------------------------------------------
    # Template generation
    # ------------------------------------------------------------------

    @staticmethod
    def create_node_template(
        name: str,
        category: str = "custom",
        description: str = "A custom pipeline node",
    ) -> dict:
        """Generate a boilerplate custom node.

        Returns a dict with ``name``, ``category``, ``code`` (Python source),
        and ``class_name``.
        """
        class_name = "".join(part.capitalize() for part in name.replace("-", "_").split("_"))
        code = NODE_TEMPLATE.format(
            class_name=class_name,
            name=name,
            category=category,
            description=description,
        )
        return {
            "name": name,
            "category": category,
            "class_name": f"{class_name}Node",
            "code": code,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_custom_node(node_code: str) -> dict:
        """Parse *node_code* and verify it defines a valid custom node.

        Checks:
        - Code is valid Python (parseable)
        - Contains a class that inherits from ``BaseNode``
        - Class has required attributes: ``name``, ``category``, ``input_schema``,
          ``output_schema``
        - Class defines an ``execute`` method
        """
        errors: list[str] = []

        # 1. Parse
        try:
            tree = ast.parse(node_code)
        except SyntaxError as exc:
            return {"valid": False, "errors": [f"SyntaxError: {exc}"]}

        # 2. Find BaseNode subclass
        node_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)
                if "BaseNode" in base_names:
                    node_classes.append(node)

        if not node_classes:
            errors.append("No class inheriting from BaseNode found.")
            return {"valid": False, "errors": errors}

        # 3. Check required attributes & methods on each node class
        for cls in node_classes:
            cls_name = cls.name
            attrs_found: set[str] = set()
            has_execute = False

            for item in cls.body:
                # Assignments (name = ..., category = ...)
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attrs_found.add(target.id)
                # Methods
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == "execute":
                        has_execute = True

            required_attrs = {"name", "category", "input_schema", "output_schema"}
            missing = required_attrs - attrs_found
            if missing:
                errors.append(
                    f"Class '{cls_name}' missing required attributes: {', '.join(sorted(missing))}"
                )
            if not has_execute:
                errors.append(f"Class '{cls_name}' missing 'execute' method.")

        return {"valid": len(errors) == 0, "errors": errors}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @staticmethod
    async def register_custom_node(
        db: AsyncSession,
        workspace_id: str,
        name: str,
        code: str,
        config: dict | None = None,
    ) -> dict:
        """Register a custom node for a workspace."""
        validation = CustomNodeSDK.validate_custom_node(code)
        if not validation["valid"]:
            return {
                "node_id": None,
                "registered": False,
                "errors": validation["errors"],
            }

        node = CustomNode(
            id=uuid.uuid4(),
            workspace_id=_as_uuid(workspace_id),
            name=name,
            code=code,
            node_metadata=config or {},
            status="registered",
        )
        db.add(node)
        await db.commit()
        return {"node_id": str(node.id), "registered": True}

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    @staticmethod
    async def list_custom_nodes(
        db: AsyncSession, workspace_id: str
    ) -> list[dict]:
        """List all custom nodes registered for a workspace."""
        result = await db.execute(
            select(CustomNode)
            .where(CustomNode.workspace_id == _as_uuid(workspace_id))
            .order_by(CustomNode.created_at)
        )
        return [
            {
                "node_id": str(node.id),
                "name": node.name,
                "workspace_id": str(node.workspace_id) if node.workspace_id else None,
                "config": node.node_metadata or {},
            }
            for node in result.scalars().all()
        ]

    # ------------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------------

    @staticmethod
    def test_custom_node(node_code: str, test_input: dict) -> dict:
        """Execute a custom node in a restricted scope and return the result.

        Returns ``result``, ``execution_time_ms``, and ``error`` (None on success).
        """
        validation = CustomNodeSDK.validate_custom_node(node_code)
        if not validation["valid"]:
            return {
                "result": {},
                "execution_time_ms": 0.0,
                "error": "; ".join(validation["errors"]),
            }

        # Build a restricted execution namespace
        restricted_globals: dict[str, Any] = {"__builtins__": {}}

        # Provide a minimal BaseNode so the import resolves
        class _BaseNode:
            name: str = ""
            category: str = ""
            description: str = ""
            input_schema: dict = {}
            output_schema: dict = {}

            async def execute(self, inputs: dict) -> dict:
                raise NotImplementedError

        # Inject the fake module path
        import types

        fake_mod = types.ModuleType("visionaudioforge")
        pipeline_mod = types.ModuleType("visionaudioforge.pipeline")
        pipeline_mod.BaseNode = _BaseNode  # type: ignore[attr-defined]
        fake_mod.pipeline = pipeline_mod  # type: ignore[attr-defined]

        import sys

        sys.modules["visionaudioforge"] = fake_mod
        sys.modules["visionaudioforge.pipeline"] = pipeline_mod

        try:
            exec(compile(node_code, "<custom_node>", "exec"), restricted_globals)  # noqa: S102
        except Exception as exc:
            return {"result": {}, "execution_time_ms": 0.0, "error": str(exc)}
        finally:
            sys.modules.pop("visionaudioforge", None)
            sys.modules.pop("visionaudioforge.pipeline", None)

        # Find the node class
        node_cls = None
        for val in restricted_globals.values():
            if isinstance(val, type) and issubclass(val, _BaseNode) and val is not _BaseNode:
                node_cls = val
                break

        if node_cls is None:
            return {"result": {}, "execution_time_ms": 0.0, "error": "No BaseNode subclass found after exec."}

        # Instantiate & run
        import asyncio

        instance = node_cls()
        start = time.perf_counter()
        try:
            result = asyncio.get_event_loop().run_until_complete(instance.execute(test_input))
        except RuntimeError:
            # If there's already a running loop, create a new one
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(instance.execute(test_input))
            finally:
                loop.close()
        except Exception as exc:
            return {"result": {}, "execution_time_ms": 0.0, "error": str(exc)}
        elapsed = (time.perf_counter() - start) * 1000

        return {"result": result, "execution_time_ms": round(elapsed, 3), "error": None}
