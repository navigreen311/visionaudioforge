"""API Documentation Generator — OpenAPI spec, Postman collection, SDK docs, curl examples."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class APIDocGenerator:
    """Generate API documentation artefacts from the running FastAPI application."""

    def __init__(self, app: Any | None = None):
        self._app = app

    @property
    def app(self):
        if self._app is None:
            from app.main import app

            self._app = app
        return self._app

    # ------------------------------------------------------------------
    # OpenAPI spec
    # ------------------------------------------------------------------

    def generate_openapi_spec(self) -> dict:
        """Return a comprehensive OpenAPI 3.0 spec derived from all FastAPI routes.

        Adds authentication info, contact details, and example payloads.
        """
        base = self.app.openapi()
        spec = dict(base)

        # Enrich with extra info
        spec.setdefault("info", {})
        spec["info"].update(
            {
                "title": "VisionAudioForge API",
                "version": getattr(self.app, "version", "0.3.0"),
                "description": (
                    "AI-powered vision & audio analysis platform. "
                    "Provides REST, WebSocket, and gRPC interfaces."
                ),
                "contact": {
                    "name": "VisionAudioForge Team",
                    "url": "https://github.com/visionaudioforge",
                },
            }
        )

        # Add security scheme
        spec.setdefault("components", {})
        spec["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        spec["security"] = [{"BearerAuth": []}]

        return spec

    # ------------------------------------------------------------------
    # SDK documentation
    # ------------------------------------------------------------------

    def generate_sdk_docs(self, language: str = "python") -> str:
        """Generate SDK usage documentation for *language* ('python' or 'javascript')."""
        if language == "python":
            return self._python_sdk_docs()
        elif language == "javascript":
            return self._javascript_sdk_docs()
        return f"Unsupported language: {language}. Use 'python' or 'javascript'."

    def _python_sdk_docs(self) -> str:
        routes = self._collect_routes()
        lines = [
            "# VisionAudioForge Python SDK",
            "",
            "## Installation",
            "```bash",
            "pip install visionaudioforge",
            "```",
            "",
            "## Quick Start",
            "```python",
            "from visionaudioforge import VAFClient",
            "",
            'client = VAFClient(base_url="http://localhost:8000", api_key="YOUR_KEY")',
            "```",
            "",
            "## Endpoints",
            "",
        ]
        for method, path in routes:
            fn_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
            lines.append(f"### {method.upper()} {path}")
            lines.append("```python")
            lines.append(f'response = client.request("{method}", "{path}")')
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    def _javascript_sdk_docs(self) -> str:
        routes = self._collect_routes()
        lines = [
            "# VisionAudioForge JavaScript SDK",
            "",
            "## Installation",
            "```bash",
            "npm install visionaudioforge",
            "```",
            "",
            "## Quick Start",
            "```javascript",
            "import { VAFClient } from 'visionaudioforge';",
            "",
            "const client = new VAFClient({",
            "  baseUrl: 'http://localhost:8000',",
            "  apiKey: 'YOUR_KEY',",
            "});",
            "```",
            "",
            "## Endpoints",
            "",
        ]
        for method, path in routes:
            lines.append(f"### {method.upper()} {path}")
            lines.append("```javascript")
            lines.append(f"const response = await client.{method}('{path}');")
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Postman collection
    # ------------------------------------------------------------------

    def generate_postman_collection(self) -> dict:
        """Generate a Postman collection JSON with all endpoints grouped by tag."""
        routes = self._collect_routes()
        grouped: dict[str, list] = {}
        for method, path in routes:
            tag = path.strip("/").split("/")[1] if "/" in path.strip("/") else "general"
            grouped.setdefault(tag, []).append((method, path))

        items = []
        for tag, endpoints in grouped.items():
            folder_items = []
            for method, path in endpoints:
                folder_items.append(
                    {
                        "name": f"{method.upper()} {path}",
                        "request": {
                            "method": method.upper(),
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{token}}"},
                                {"key": "Content-Type", "value": "application/json"},
                            ],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": [p for p in path.strip("/").split("/") if p],
                            },
                        },
                    }
                )
            items.append({"name": tag, "item": folder_items})

        return {
            "info": {
                "name": "VisionAudioForge API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "description": "Auto-generated Postman collection for VisionAudioForge.",
            },
            "variable": [
                {"key": "base_url", "value": "http://localhost:8000"},
                {"key": "token", "value": ""},
            ],
            "item": items,
        }

    # ------------------------------------------------------------------
    # Curl examples
    # ------------------------------------------------------------------

    def generate_curl_examples(self) -> dict[str, str]:
        """Generate a curl command string for each endpoint."""
        routes = self._collect_routes()
        examples: dict[str, str] = {}
        for method, path in routes:
            key = f"{method.upper()} {path}"
            if method.upper() in ("POST", "PUT", "PATCH"):
                examples[key] = (
                    f"curl -X {method.upper()} http://localhost:8000{path} "
                    f'-H "Authorization: Bearer $TOKEN" '
                    f'-H "Content-Type: application/json" '
                    f"-d '{{}}'"
                )
            else:
                examples[key] = (
                    f"curl -X {method.upper()} http://localhost:8000{path} "
                    f'-H "Authorization: Bearer $TOKEN"'
                )
        return examples

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_routes(self) -> list[tuple[str, str]]:
        """Return a sorted list of ``(method, path)`` tuples from the app."""
        routes: list[tuple[str, str]] = []
        for route in self.app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    if method.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                        routes.append((method.lower(), route.path))
        routes.sort(key=lambda r: (r[1], r[0]))
        return routes
