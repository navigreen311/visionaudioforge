"""Copilot service — Claude API streaming chat with memory and tool use."""

import json
import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.services.agents.skill_packs import SKILL_PACKS
from app.services.agents.tools import COPILOT_TOOLS, execute_tool

logger = logging.getLogger(__name__)


class CopilotService:
    """Agentic media copilot powered by Claude API with streaming, memory, and tools."""

    def __init__(self) -> None:
        self._client = None
        if settings.ANTHROPIC_API_KEY:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=settings.ANTHROPIC_API_KEY
                )
            except ImportError:
                logger.warning(
                    "anthropic package not installed. Copilot will run in mock mode."
                )
        else:
            logger.warning(
                "ANTHROPIC_API_KEY not set. Copilot will run in mock mode."
            )

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def chat(
        self,
        message: str,
        workspace_id: str,
        agent_id: str,
        context: dict | None = None,
        skill_pack: str = "general",
        memories: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream a chat response from Claude.

        Yields dicts with type: "token", "tool_use", or "done".
        """
        system_prompt = self._build_system_prompt(
            workspace_id, agent_id, skill_pack=skill_pack, memories=memories
        )

        messages = []
        if context and context.get("history"):
            messages.extend(context["history"])
        messages.append({"role": "user", "content": message})

        if not self.is_available:
            # Mock mode for development without API key
            mock_response = (
                f"[Mock Copilot | {skill_pack}] I received your message: "
                f'"{message}". The Anthropic API key is not configured, so I\'m '
                "running in mock mode. Configure ANTHROPIC_API_KEY to enable "
                "full copilot capabilities."
            )
            for word in mock_response.split(" "):
                yield {"type": "token", "content": word + " "}
            yield {"type": "done"}
            return

        # Stream from Claude API
        async with self._client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=self._get_tools(),
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            yield {
                                "type": "tool_use_start",
                                "tool": event.content_block.name,
                                "id": event.content_block.id,
                            }

                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"type": "token", "content": event.delta.text}
                    elif hasattr(event.delta, "partial_json"):
                        yield {
                            "type": "tool_input_delta",
                            "content": event.delta.partial_json,
                        }

                elif event.type == "content_block_stop":
                    pass

                elif event.type == "message_stop":
                    pass

        # Check if the final message has tool use blocks that need execution
        final_message = await stream.get_final_message()
        for block in final_message.content:
            if block.type == "tool_use":
                tool_result = await self._execute_tool(block.name, block.input)
                yield {
                    "type": "tool_result",
                    "tool": block.name,
                    "input": block.input,
                    "result": tool_result,
                }

        yield {"type": "done"}

    def _build_system_prompt(
        self,
        workspace_id: str,
        agent_id: str,
        skill_pack: str = "general",
        memories: list[str] | None = None,
    ) -> str:
        """Build a system prompt with role, tools, and context."""
        persona = SKILL_PACKS.get(skill_pack, SKILL_PACKS["general"])

        tool_names = [t["name"] for t in COPILOT_TOOLS]
        tools_section = ", ".join(tool_names)

        sections = [
            persona,
            "",
            "## Platform",
            "You are integrated into VisionAudioForge, an AI-powered vision and audio "
            "analysis platform. You operate within a workspace and have access to tools.",
            "",
            "## Available Tools",
            f"You can use these tools: {tools_section}.",
            "Use tools when the user's request requires data retrieval, analysis, or "
            "system actions. Always explain what you found after using a tool.",
            "",
            f"## Context",
            f"Workspace ID: {workspace_id}",
            f"Agent ID: {agent_id}",
        ]

        if memories:
            sections.append("")
            sections.append("## Relevant Memories")
            for mem in memories:
                sections.append(f"- {mem}")

        return "\n".join(sections)

    def _get_tools(self) -> list[dict]:
        """Return tool definitions in Claude tool_use format."""
        return COPILOT_TOOLS

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return the result."""
        return await execute_tool(tool_name, tool_input)
