"""Copilot service — Claude API streaming chat with memory, tools, and context enrichment."""

import json
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.agents.conversation import ConversationManager
from app.services.agents.skill_packs import SKILL_PACKS
from app.services.agents.tools import COPILOT_TOOLS, execute_tool

logger = logging.getLogger(__name__)

conversation_manager = ConversationManager()


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
        db: AsyncSession | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream a chat response from Claude.

        Yields dicts with type: "token", "tool_use", "tool_result", or "done".
        """
        # Store user message in conversation history
        if db is not None:
            try:
                await conversation_manager.store_message(db, agent_id, "user", message)
            except Exception as exc:
                logger.warning("Failed to store user message: %s", exc)

        # Build system prompt with enrichment (including graph context)
        system_prompt = await self._build_system_prompt(
            workspace_id, agent_id, skill_pack=skill_pack, memories=memories, db=db,
            user_message=message,
        )

        # Build messages list with conversation history
        messages = []
        if db is not None:
            try:
                history = await conversation_manager.get_context_window(db, agent_id, max_tokens_approx=3000)
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})
            except Exception as exc:
                logger.warning("Failed to load conversation history: %s", exc)

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

            # Store assistant response
            if db is not None:
                try:
                    await conversation_manager.store_message(db, agent_id, "assistant", mock_response)
                except Exception as exc:
                    # store_message commits. Dropping that in silence loses
                    # conversation history with no trace — and this is the mock
                    # branch, which is what runs whenever ANTHROPIC_API_KEY is
                    # unset, i.e. by default. The real-API path below logs the
                    # same failure; these two disagreed.
                    logger.warning("Failed to store assistant message: %s", exc)

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
        full_response_parts = []

        for block in final_message.content:
            if block.type == "text":
                full_response_parts.append(block.text)
            elif block.type == "tool_use":
                tool_result = await self._execute_tool(block.name, block.input)
                yield {
                    "type": "tool_result",
                    "tool": block.name,
                    "input": block.input,
                    "result": tool_result,
                }

        # Store assistant response in conversation history
        response_text = "".join(full_response_parts)
        if db is not None and response_text:
            try:
                await conversation_manager.store_message(db, agent_id, "assistant", response_text)
                await self._auto_store_memory(db, agent_id, response_text, context)
            except Exception as exc:
                logger.warning("Failed to store assistant message: %s", exc)

        yield {"type": "done"}

    async def _build_system_prompt(
        self,
        workspace_id: str,
        agent_id: str,
        skill_pack: str = "general",
        memories: list[str] | None = None,
        db: AsyncSession | None = None,
        user_message: str | None = None,
    ) -> str:
        """Build a system prompt with role, tools, context enrichment."""
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

        # Context enrichment: patrol findings and workspace stats
        if db is not None:
            try:
                patrol_section = await self._get_patrol_context(agent_id, db)
                if patrol_section:
                    sections.append("")
                    sections.append(patrol_section)
            except Exception as exc:
                logger.debug("patrol context unavailable for system prompt: %s", exc)

            try:
                stats_section = await self._get_workspace_stats(db)
                if stats_section:
                    sections.append("")
                    sections.append(stats_section)
            except Exception as exc:
                logger.debug("workspace stats unavailable for system prompt: %s", exc)

            try:
                memory_summary = await self._get_memory_summary(agent_id, db)
                if memory_summary:
                    sections.append("")
                    sections.append(memory_summary)
            except Exception as exc:
                logger.debug("memory summary unavailable for system prompt: %s", exc)

            # Knowledge graph context enrichment
            if user_message:
                try:
                    graph_context = await self._get_graph_context(
                        db, user_message, workspace_id
                    )
                    if graph_context:
                        sections.append("")
                        sections.append(graph_context)
                except Exception as exc:
                    logger.debug("graph context unavailable for system prompt: %s", exc)

        return "\n".join(sections)

    async def _get_patrol_context(self, agent_id: str, db: AsyncSession) -> str | None:
        """Get recent patrol findings for context."""
        try:
            from app.services.agents.patrol import get_patrol_agent

            patrol = get_patrol_agent(agent_id)
            report = await patrol.get_patrol_report(db, hours=24)
            findings = report.get("findings", [])[:5]
            if not findings:
                return None

            lines = ["## Recent Patrol Findings"]
            for f in findings:
                lines.append(f"- [{f['status'].upper()}] {f['check']}: {f['message']}")
            return "\n".join(lines)
        except Exception:
            return None

    async def _get_workspace_stats(self, db: AsyncSession) -> str | None:
        """Get workspace statistics for context enrichment."""
        try:
            from sqlalchemy import func, select

            from app.models.alert import Alert, AlertStatus
            from app.models.asset import Asset
            from app.models.model_registry import ModelRecord

            asset_count = (await db.execute(select(func.count()).select_from(Asset))).scalar() or 0
            model_count = (await db.execute(select(func.count()).select_from(ModelRecord))).scalar() or 0
            alert_count = (
                await db.execute(
                    select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.new)
                )
            ).scalar() or 0

            return (
                "## Workspace Statistics\n"
                f"- Total assets: {asset_count}\n"
                f"- Registered models: {model_count}\n"
                f"- Active alerts: {alert_count}"
            )
        except Exception:
            return None

    async def _get_memory_summary(self, agent_id: str, db: AsyncSession) -> str | None:
        """Get a conversation summary from memory service."""
        try:
            from app.services.agents.memory import AgentMemoryService

            mem_svc = AgentMemoryService()
            summary = await mem_svc.get_memory_summary(db, agent_id)
            if summary["total_memories"] == 0:
                return None

            lines = [
                "## Memory Summary",
                f"- Total memories: {summary['total_memories']}",
                f"- Avg importance: {summary['avg_importance']}",
                f"- Recent (24h): {summary['recent_count']}",
            ]
            if summary["top_memories"]:
                lines.append("- Top memories:")
                for m in summary["top_memories"][:3]:
                    lines.append(f"  - {m[:100]}")
            return "\n".join(lines)
        except Exception:
            return None

    async def _get_graph_context(
        self, db: AsyncSession, user_message: str, workspace_id: str
    ) -> str | None:
        """Retrieve knowledge graph context relevant to the user's message."""
        try:
            from app.services.knowledge_graph.graph_rag import GraphRAGService

            graph_rag = GraphRAGService()
            augmentation = await graph_rag.augment_copilot_prompt(
                db, user_message, workspace_id
            )
            if augmentation:
                return f"## {augmentation}"
            return None
        except Exception:
            return None

    async def _auto_store_memory(
        self,
        db: AsyncSession,
        agent_id: str,
        response_text: str,
        context: dict | None,
    ) -> None:
        """Analyze response for important facts and auto-store high-importance memories."""
        # Heuristic: store memories for responses that contain key events/decisions
        important_keywords = [
            "alert", "critical", "warning", "error", "created", "deployed",
            "promoted", "detected", "anomaly", "incident", "resolved",
            "decision", "recommend", "action required",
        ]

        response_lower = response_text.lower()
        keyword_hits = sum(1 for kw in important_keywords if kw in response_lower)

        if keyword_hits >= 2 and len(response_text) > 50:
            importance = min(0.5 + (keyword_hits * 0.1), 0.9)
            try:
                from app.services.agents.memory import AgentMemoryService

                mem_svc = AgentMemoryService()
                # Store a condensed version
                summary = response_text[:300]
                await mem_svc.store_memory(db, agent_id, summary, importance_score=importance)
                logger.debug("Auto-stored memory (importance=%.2f) for agent %s", importance, agent_id)
            except Exception as exc:
                logger.warning("Failed to auto-store memory: %s", exc)

    def _get_tools(self) -> list[dict]:
        """Return tool definitions in Claude tool_use format."""
        return COPILOT_TOOLS

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return the result."""
        return await execute_tool(tool_name, tool_input)
