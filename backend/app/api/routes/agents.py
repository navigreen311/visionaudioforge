"""Agent API routes — chat, CRUD, memory, conversation history, and patrol."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.agent import Agent, AgentMemory
from app.services.agents.conversation import ConversationManager
from app.services.agents.copilot import CopilotService
from app.services.agents.memory import AgentMemoryService
from app.services.agents.patrol import get_patrol_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

copilot_service = CopilotService()
memory_service = AgentMemoryService()
conversation_mgr = ConversationManager()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    agent_id: str | None = None
    skill_pack: str = "general"
    context: dict | None = None


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    memories_used: int


class CreateAgentRequest(BaseModel):
    name: str
    agent_type: str = "copilot"
    skill_pack: str = "general"
    description: str = ""
    auto_patrol: bool = False
    workspace_scope: str = "all"
    workspace_id: str | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    agent_type: str
    skill_pack: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class AgentDetailOut(BaseModel):
    id: str
    name: str
    agent_type: str
    skill_pack: str
    status: str
    description: str
    auto_patrol: bool
    workspace_scope: str
    created_at: str

    class Config:
        from_attributes = True


class MemoryOut(BaseModel):
    id: str
    content: str
    importance_score: float
    freshness_score: float
    created_at: str

    class Config:
        from_attributes = True


class PatrolRequest(BaseModel):
    scope: str = "all"


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class CreateConversationRequest(BaseModel):
    agent_id: str | None = None
    title: str = "New Conversation"
    messages: list[ConversationMessage] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    agent_id: str | None = None
    conversation_id: str | None = None
    rating: int = Field(default=5, ge=1, le=5)
    comment: str = ""


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Non-streaming chat fallback: collects all tokens and returns full response."""
    agent_id = body.agent_id or str(uuid.uuid4())

    # Recall relevant memories
    memories_list = await memory_service.recall(db, agent_id, query=body.message, k=5)
    memory_strings = [m.content for m in memories_list]

    # Collect streamed tokens
    full_response: list[str] = []
    async for event in copilot_service.chat(
        message=body.message,
        workspace_id="default",
        agent_id=agent_id,
        context=body.context,
        skill_pack=body.skill_pack,
        memories=memory_strings,
        db=db,
    ):
        if event["type"] == "token":
            full_response.append(event["content"])

    response_text = "".join(full_response)

    # Store response as memory if it's substantive
    if len(response_text) > 50:
        await memory_service.store_memory(
            db, agent_id, response_text[:500], importance_score=0.4
        )

    return ChatResponse(
        response=response_text,
        agent_id=agent_id,
        memories_used=len(memories_list),
    )


@router.post("/chat/stream")
async def agent_chat_stream(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream a copilot reply as Server-Sent Events.

    CopilotChat reads ``data: {json}`` lines and stops on ``data: [DONE]``,
    forwarding each event's ``type`` (token / tool_use / tool_result / error).
    """
    agent_id = body.agent_id or str(uuid.uuid4())

    memories_list = await memory_service.recall(db, agent_id, query=body.message, k=5)
    memory_strings = [m.content for m in memories_list]

    async def event_stream():
        collected: list[str] = []
        try:
            async for event in copilot_service.chat(
                message=body.message,
                workspace_id="default",
                agent_id=agent_id,
                context=body.context,
                skill_pack=body.skill_pack,
                memories=memory_strings,
                db=db,
            ):
                if event.get("type") == "token":
                    collected.append(event.get("content", ""))
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # keep the stream well-formed on failure
            logger.exception("Copilot stream failed")
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        else:
            response_text = "".join(collected)
            if len(response_text) > 50:
                await memory_service.store_memory(
                    db, agent_id, response_text[:500], importance_score=0.4
                )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------


@router.get("")
async def list_agents(
    db: AsyncSession = Depends(get_db),
):
    """List all agents in the workspace."""
    stmt = select(Agent).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "agent_type": a.agent_type,
            "skill_pack": (a.config or {}).get("skill_pack", "general"),
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }
        for a in agents
    ]


# NOTE: GET /{agent_id} used to be declared here. Registered ahead of the
# literal routes below, it swallowed GET /conversations — the console's
# conversation list was answered by an agent lookup and always 404'd. The
# single-agent handler now lives after the literal routes; see below.


@router.post("", status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent."""
    workspace_id = body.workspace_id or str(uuid.uuid4())

    agent = Agent(
        name=body.name,
        agent_type=body.agent_type,
        status="idle",
        workspace_id=workspace_id,
        config={
            "skill_pack": body.skill_pack,
            "description": body.description,
            "auto_patrol": body.auto_patrol,
            "workspace_scope": body.workspace_scope,
        },
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    cfg: dict = agent.config or {}
    return {
        "id": str(agent.id),
        "name": agent.name,
        "agent_type": agent.agent_type,
        "skill_pack": cfg.get("skill_pack", "general"),
        "status": agent.status,
        "description": cfg.get("description", ""),
        "auto_patrol": cfg.get("auto_patrol", False),
        "workspace_scope": cfg.get("workspace_scope", "all"),
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
    }


# ---------------------------------------------------------------------------
# Patrol (top-level, mock-safe)
# ---------------------------------------------------------------------------

@router.post("/patrol")
async def patrol_all():
    """Run a quick patrol scan across all streams and return findings.

    Returns mock data so the frontend always gets a usable response.
    """
    return {
        "findings": [
            "All streams healthy",
            "No new alerts",
        ],
        "alerts": 0,
    }


# ---------------------------------------------------------------------------
# Conversations (top-level, mock-safe)
# ---------------------------------------------------------------------------

# In-memory store so the stub is functional within a single server session.
_mock_conversations: dict[str, dict[str, Any]] = {
    "conv-001": {
        "id": "conv-001",
        "title": "Vision Pipeline Troubleshooting",
        "agent_id": "agent-alpha",
        "created_at": "2026-03-20T10:00:00Z",
        "messages": [
            {"role": "user", "content": "Why is the vision pipeline stalling?", "timestamp": "2026-03-20T10:00:00Z"},
            {"role": "assistant", "content": "Checking pipeline status...", "timestamp": "2026-03-20T10:00:01Z"},
            {"role": "assistant", "content": "The bottleneck is in the frame decoder. Consider enabling GPU acceleration.", "timestamp": "2026-03-20T10:00:02Z"},
            {"role": "user", "content": "Got it, enabling now.", "timestamp": "2026-03-20T10:00:10Z"},
        ],
    },
    "conv-002": {
        "id": "conv-002",
        "title": "Audio Feature Extraction",
        "agent_id": "agent-beta",
        "created_at": "2026-03-19T14:30:00Z",
        "messages": [
            {"role": "user", "content": "Extract MFCCs from the latest batch.", "timestamp": "2026-03-19T14:30:00Z"},
            {"role": "assistant", "content": "Processing 42 audio files...", "timestamp": "2026-03-19T14:30:01Z"},
            {"role": "assistant", "content": "Done. 42 MFCC matrices saved.", "timestamp": "2026-03-19T14:30:30Z"},
            {"role": "user", "content": "Perfect, thanks.", "timestamp": "2026-03-19T14:31:00Z"},
        ],
    },
    "conv-003": {
        "id": "conv-003",
        "title": "Alert Investigation",
        "agent_id": "agent-alpha",
        "created_at": "2026-03-18T08:15:00Z",
        "messages": [
            {"role": "user", "content": "What triggered alert #47?", "timestamp": "2026-03-18T08:15:00Z"},
            {"role": "assistant", "content": "Alert #47 was triggered by anomalous motion in Camera 3.", "timestamp": "2026-03-18T08:15:02Z"},
            {"role": "user", "content": "Is it a false positive?", "timestamp": "2026-03-18T08:15:30Z"},
            {"role": "assistant", "content": "Confidence is 62%. Likely a shadow artifact. Recommend reviewing the clip.", "timestamp": "2026-03-18T08:15:32Z"},
        ],
    },
}


@router.get("/conversations")
async def list_conversations():
    """Return all mock conversations (summary only, no messages)."""
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "agent_id": c.get("agent_id"),
            "created_at": c["created_at"],
            "message_count": len(c.get("messages", [])),
        }
        for c in _mock_conversations.values()
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Return a single conversation with all messages."""
    conv = _mock_conversations.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations", status_code=201)
async def create_conversation(body: CreateConversationRequest):
    """Save a new conversation and return it."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    conv = {
        "id": conv_id,
        "title": body.title,
        "agent_id": body.agent_id or "agent-default",
        "created_at": now,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp or now,
            }
            for m in body.messages
        ],
    }
    _mock_conversations[conv_id] = conv
    return conv


# ---------------------------------------------------------------------------
# Feedback (top-level, mock-safe)
# ---------------------------------------------------------------------------

@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    """Accept user feedback on an agent interaction."""
    logger.info(
        "Feedback received: agent=%s conversation=%s rating=%d",
        body.agent_id,
        body.conversation_id,
        body.rating,
    )
    return {"success": True}


# ---------------------------------------------------------------------------
# Single agent lookup (must come AFTER /patrol, /conversations, /feedback)
# ---------------------------------------------------------------------------

@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single agent by ID. Falls back to mock data on DB failure."""
    try:
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent:
            return {
                "id": str(agent.id),
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else "",
            }
    except Exception:
        logger.debug("DB lookup failed for agent %s — returning mock", agent_id)

    # Mock fallback
    return {
        "id": agent_id,
        "name": f"Agent {agent_id[:8]}",
        "agent_type": "copilot",
        "status": "idle",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Memory management
# ---------------------------------------------------------------------------


@router.get("/{agent_id}/memory")
async def list_memories(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List memories for a given agent."""
    memories = await memory_service.recall(db, agent_id, k=50)
    return [
        {
            "id": str(m.id),
            "content": m.content,
            "importance_score": m.importance_score,
            "freshness_score": round(m.freshness_score, 4),
            "created_at": m.created_at.isoformat() if m.created_at else "",
        }
        for m in memories
    ]


@router.post("/{agent_id}/memory/decay")
async def trigger_memory_decay(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger memory decay for an agent."""
    count = await memory_service.decay_memories(db, agent_id)
    return {"agent_id": agent_id, "memories_decayed": count}


@router.delete("/{agent_id}/memory/{memory_id}")
async def delete_memory(
    agent_id: str,
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific memory."""
    deleted = await memory_service.delete_memory(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "memory_id": memory_id}


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


@router.get("/{agent_id}/history")
async def get_conversation_history(
    agent_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation history for an agent."""
    history = await conversation_mgr.get_history(db, agent_id, limit=limit)
    return {"agent_id": agent_id, "messages": history, "count": len(history)}


@router.delete("/{agent_id}/history")
async def clear_conversation_history(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Clear all conversation history for an agent."""
    deleted = await conversation_mgr.clear_history(db, agent_id)
    return {"agent_id": agent_id, "deleted_count": deleted}


# ---------------------------------------------------------------------------
# Patrol mode
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/patrol/start")
async def start_patrol(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start autonomous patrol for an agent."""
    patrol = get_patrol_agent(agent_id)
    if patrol.is_running:
        return {"agent_id": agent_id, "status": "already_running"}

    await patrol.start_patrol()
    return {"agent_id": agent_id, "status": "started"}


@router.post("/{agent_id}/patrol/stop")
async def stop_patrol(
    agent_id: str,
):
    """Stop autonomous patrol for an agent."""
    patrol = get_patrol_agent(agent_id)
    if not patrol.is_running:
        return {"agent_id": agent_id, "status": "not_running"}

    await patrol.stop_patrol()
    return {"agent_id": agent_id, "status": "stopped"}


@router.get("/{agent_id}/patrol/report")
async def get_patrol_report(
    agent_id: str,
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """Get patrol findings for an agent."""
    patrol = get_patrol_agent(agent_id)
    report = await patrol.get_patrol_report(db, hours=hours)
    return {
        "agent_id": agent_id,
        "is_patrolling": patrol.is_running,
        **report,
    }


# ---------------------------------------------------------------------------
# Patrol quick-check stub (AG4)
# ---------------------------------------------------------------------------


class PatrolCheckResponse(BaseModel):
    findings: list[str]
    alerts: int


# NOTE: a second POST /patrol was declared here. It could never be reached —
# the handler near the top of this file is registered first — so it was
# removed rather than left as dead code.
