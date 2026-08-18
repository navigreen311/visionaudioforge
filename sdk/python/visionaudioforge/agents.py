"""Copilot / Agent API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import Agent, Memory

if TYPE_CHECKING:
    from .client import VAFClient


class AgentClient:
    """Wraps the /api/agents endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def chat(
        self,
        message: str,
        agent_id: str | None = None,
        skill_pack: str = "general",
    ) -> str:
        """Send a chat message to an agent and return the response text."""
        payload: dict[str, Any] = {"message": message, "skill_pack": skill_pack}
        if agent_id:
            payload["agent_id"] = agent_id
        resp = await self._client._request(
            "POST", "/api/agents/chat", json=payload
        )
        return resp.get("response", "") if isinstance(resp, dict) else str(resp)

    async def list_agents(self) -> list[Agent]:
        """List available agents."""
        resp = await self._client._request("GET", "/api/agents")
        items = resp if isinstance(resp, list) else resp.get("agents", [])
        return [Agent.model_validate(a) for a in items]

    async def get_memory(self, agent_id: str) -> list[Memory]:
        """Retrieve an agent's memory entries."""
        resp = await self._client._request(
            "GET", f"/api/agents/{agent_id}/memory"
        )
        items = resp if isinstance(resp, list) else resp.get("memories", [])
        return [Memory.model_validate(m) for m in items]
