"""Agent API routes — chat, CRUD, and memory management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.agent import Agent, AgentMemory
from app.services.agents.copilot import CopilotService
from app.services.agents.memory import AgentMemoryService

router = APIRouter(prefix="/api/agents", tags=["agents"])

copilot_service = CopilotService()
memory_service = AgentMemoryService()


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
