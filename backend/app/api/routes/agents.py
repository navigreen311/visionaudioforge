"""Agent API routes — chat, CRUD, memory, conversation history, and patrol."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.agent import Agent, AgentMemory
from app.services.agents.conversation import ConversationManager
from app.services.agents.copilot import CopilotService
from app.services.agents.memory import AgentMemoryService
from app.services.agents.patrol import get_patrol_agent

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
    workspace_id: str | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
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


class ConversationMessageIn(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    timestamp: str
    tool_name: str | None = None


class SaveConversationRequest(BaseModel):
    summary: str
    skill_pack: str = "general"
    messages: list[ConversationMessageIn] = Field(default_factory=list)


class ConversationSummaryOut(BaseModel):
    id: str
    summary: str
    skill_pack: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetailOut(BaseModel):
    id: str
    summary: str
    skill_pack: str
    messages: list[ConversationMessageIn]
    created_at: str
    updated_at: str


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
    full_response = []
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
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }
        for a in agents
    ]


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
        config={},
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return {
        "id": str(agent.id),
        "name": agent.name,
        "agent_type": agent.agent_type,
        "status": agent.status,
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
    }


# ---------------------------------------------------------------------------
# Conversations (AG5) — stub endpoints
# IMPORTANT: These MUST be registered before /{agent_id} routes to avoid
# FastAPI matching "conversations" as an agent_id path parameter.
# ---------------------------------------------------------------------------

# In-memory store (stub — replace with DB persistence)
_conversations_store: dict[str, dict[str, object]] = {}


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def list_conversations():
    """List all saved conversations (newest first)."""
    items = sorted(
        _conversations_store.values(),
        key=lambda c: str(c.get("updated_at", "")),
        reverse=True,
    )
    return [
        ConversationSummaryOut(
            id=str(c["id"]),
            summary=str(c["summary"]),
            skill_pack=str(c["skill_pack"]),
            message_count=len(c.get("messages", [])),  # type: ignore[arg-type]
            created_at=str(c["created_at"]),
            updated_at=str(c["updated_at"]),
        )
        for c in items
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(conversation_id: str):
    """Load a specific conversation with its messages."""
    conv = _conversations_store.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailOut(
        id=str(conv["id"]),
        summary=str(conv["summary"]),
        skill_pack=str(conv["skill_pack"]),
        messages=conv.get("messages", []),  # type: ignore[arg-type]
        created_at=str(conv["created_at"]),
        updated_at=str(conv["updated_at"]),
    )


@router.post("/conversations", response_model=ConversationSummaryOut, status_code=201)
async def save_conversation(body: SaveConversationRequest):
    """Save a conversation (creates a new entry)."""
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": conv_id,
        "summary": body.summary,
        "skill_pack": body.skill_pack,
        "messages": [m.model_dump() for m in body.messages],
        "created_at": now,
        "updated_at": now,
    }
    _conversations_store[conv_id] = entry
    return ConversationSummaryOut(
        id=conv_id,
        summary=body.summary,
        skill_pack=body.skill_pack,
        message_count=len(body.messages),
        created_at=now,
        updated_at=now,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a saved conversation."""
    if conversation_id not in _conversations_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del _conversations_store[conversation_id]
    return {"deleted": True, "id": conversation_id}


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


@router.post("/patrol", response_model=PatrolCheckResponse)
async def patrol_quick_check() -> PatrolCheckResponse:
    """Quick patrol check — returns current system health summary."""
    return PatrolCheckResponse(
        findings=["All streams healthy"],
        alerts=0,
    )
